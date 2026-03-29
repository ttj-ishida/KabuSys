CHANGELOG
=========

すべての重要な変更は Keep a Changelog の方針に従って記載しています。  
このファイルはリポジトリ内のコードから推測して作成した初期の変更履歴です。

[Unreleased]
-------------

- （なし）

[0.1.0] - 2026-03-29
--------------------

初回リリース。パッケージ kabusys のコア機能を追加。

Added
- パッケージ基盤
  - パッケージ初期化: src/kabusys/__init__.py にてバージョン "0.1.0" と主要サブパッケージ（data, research, ai, monitoring?）のエクスポートを定義。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env ファイルや環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルートの検出は __file__ を起点に .git または pyproject.toml を探索（配布後の動作安定化）。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート。
    - 読み込み時に OS 環境変数キーを保護（protected set）して上書きを制御。
  - .env パーサーは export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ、コメント処理（クォートあり無しのケース）に対応。
  - Settings クラスを提供し、J-Quants・kabuステーション・Slack・DB パス・環境種別（development/paper_trading/live）・ログレベル等のプロパティを取得。無効 or 未設定時は ValueError を発生させる検証を実装。

- AI モジュール（src/kabusys/ai）
  - ニュース NLU（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約し、銘柄ごとにニューステキストを結合して OpenAI (gpt-4o-mini) に送信。
    - バッチ処理（最大 20 銘柄/チャンク）、記事数・文字数トリム、JSON Mode（厳密な JSON 出力）を前提としたパース／検証ロジックを実装。
    - リトライ（429・ネットワーク断・タイムアウト・5xx）を指数バックオフで実施。非リトライエラーはスキップして継続するフェイルセーフ設計。
    - レスポンス検証: JSON 抽出、"results" リスト、code/score の型チェック、スコアの ±1.0 クリップ。
    - 書き込み: 成功取得した銘柄のみ ai_scores テーブルを置換（DELETE → INSERT）し、部分失敗時に既存スコアを保護。
    - 単体テスト用フック: _call_openai_api を patch して差し替え可能。
    - calc_news_window 関数: タイムウィンドウ（JST 前日 15:00 ～ 当日 08:30）を UTC naive datetime で返すユーティリティ。
  - レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定する score_regime を実装。
    - MA 計算は target_date 未満のデータのみを利用してルックアヘッドバイアスを防止。
    - マクロ記事のフィルタリングはマクロキーワード一覧に基づき raw_news から取得、LLM 呼び出しは最大リトライ回数を設けてフォールバック（失敗時 macro_sentiment=0.0）。
    - OpenAI 呼び出しは client を生成して行い、api_key 引数または環境変数 OPENAI_API_KEY を利用。
    - 市場レジームは冪等に market_regime テーブルへ書き込み（BEGIN/DELETE/INSERT/COMMIT）し、書き込み失敗時は ROLLBACK。

- Research モジュール（src/kabusys/research）
  - factor_research.py:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率等を計算。
    - calc_value: raw_financials から EPS/ROE を組み合わせて PER/ROE を算出。
    - DuckDB SQL を活用し、営業日バッファ等を用いて過去データ不足を扱う。
  - feature_exploration.py:
    - calc_forward_returns: 任意ホライズンの将来リターンを一括で取得（horizons の検証あり）。
    - calc_ic: スピアマンランク相関（IC）を計算。データ不足時は None を返す。
    - rank / factor_summary: ランク化、基本統計量算出ユーティリティ。
  - data.stats の zscore_normalize を再エクスポート。

- Data プラットフォーム（src/kabusys/data）
  - calendar_management.py:
    - JPX マーケットカレンダー管理: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day 等のユーティリティを提供。
    - DB（market_calendar）にデータがある場合は DB 値を優先、未登録日は曜日ベースでフォールバック。最大探索日数による安全策を実装。
    - calendar_update_job: J-Quants API (jquants_client) から差分取得し market_calendar を冪等に更新。バックフィルと健全性チェック（未来日チェック）を実装。
  - pipeline.py / etl.py:
    - ETLResult データクラスを追加（ETL 実行結果、品質問題、エラー一覧などを格納）。
    - パイプライン設計: 差分更新、backfill、品質チェック（quality モジュールとの連携）、id_token 注入によるテスト容易化。
    - DuckDB の互換性考慮（executemany に空リストを渡さない等）や冪等保存（ON CONFLICT 相当）を想定した実装。

- 全体設計上の注意点（ドキュメント化／実装）
  - ルックアヘッドバイアス対策: datetime.today()/date.today() を主要ロジックで直接参照しない（target_date ベースの計算）。
  - OpenAI 呼び出し周りはリトライ（指数バックオフ）・5xx とそれ以外の扱いを明確化し、API 失敗時は例外を投げずフォールバックする設計が多く採用されている（フェイルセーフ）。
  - DB 書き込みは冪等化（DELETE → INSERT）やトランザクション（BEGIN/COMMIT/ROLLBACK）を利用し、ROLLBACK 失敗時のログ出力も考慮。
  - テスト促進のため _call_openai_api 等の内部関数をモック差し替え可能にしている。
  - DuckDB を主なローカル分析用 DB として使用。DuckDB バージョン差分に関する互換性コメントあり（e.g. executemany 空リストの挙動）。

Changed
- （新規初回リリースのため該当なし）

Fixed
- （新規初回リリースのため該当なし）

Notes / Known limitations
- OpenAI API キーが未設定の場合、score_news / score_regime は ValueError を送出する。CI / 実行環境では OPENAI_API_KEY の設定が必要。
- DuckDB のバージョン差に依存する挙動について注記あり（executemany と空リスト等）。運用環境に合わせて確認が必要。
- 一部のテーブル（market_calendar, prices_daily, raw_news, raw_financials, news_symbols, ai_scores, market_regime 等）を前提としているため、初期スキーマ準備が必要。
- 現段階では PBR や配当利回りなど一部バリューファクターは未実装（calc_value の注記参照）。

--- 

この CHANGELOG はコードからの推測を元に記載しています。実際のリリースノート作成時はコミット履歴や PR / issue の情報を参照し、日付・詳細を適宜更新してください。