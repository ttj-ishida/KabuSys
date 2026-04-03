Keep a Changelog
=================

すべての重要な変更点をこのファイルで管理します。  
フォーマットは "Keep a Changelog" に準拠しています。

[Unreleased]
------------

（現在なし）

[0.1.0] - 2026-04-03
-------------------

初回公開リリース。日本株自動売買システムのコアライブラリを提供します。主な追加点は以下の通りです。

Added
- パッケージ基盤
  - kabusys パッケージ初期実装。
  - バージョン: 0.1.0 を src/kabusys/__init__.py に定義。
  - パブリックモジュールとして data, research, ai, （将来的に strategy / execution / monitoring を想定）をエクスポートする準備。

- 環境設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env と .env.local の優先順を実装（OS 環境変数の保護機構あり）。
  - .env 行パーサの実装（コメント、export 形式、シングル/ダブルクォート、エスケープ対応）。
  - Settings クラスを提供し、J-Quants / kabuAPI / LINE / DB パス / 監視閾値 / 環境モード（development/paper_trading/live）等のプロパティを用意。
  - 必須変数未設定時に ValueError を投げる _require 実装。
  - LOG_LEVEL / KABUSYS_ENV の値検証を実装（不正値は ValueError）。

- データ基盤（kabusys.data）
  - ETL 関連:
    - ETLResult dataclass（pipeline.ETLResult）を公開（kabusys.data.etl / pipeline）。
    - pipeline モジュールに ETLResult と ETL ユーティリティ群の骨格を実装（差分更新、バックフィル、品質チェック方針の記述）。
    - DuckDB を前提とした DB 操作ユーティリティ（テーブル存在チェック、最大日付取得、executemany の空リスト制約に対する注意等）。
  - マーケットカレンダー管理:
    - market_calendar を使った営業日判定ロジックを実装（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB データ優先、未登録日は曜日ベースでフォールバックする一貫した挙動。
    - calendar_update_job: J-Quants から差分取得して冪等的に保存するバッチロジック（バックフィル・健全性チェック含む）。
    - 最大探索日数や先読み日数など安全パラメータを導入（_MAX_SEARCH_DAYS / _CALENDAR_LOOKAHEAD_DAYS / _BACKFILL_DAYS / _SANITY_MAX_FUTURE_DAYS）。

- AI ニュース解析（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を基に銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄別センチメント（-1.0〜1.0）を算出。
    - 対象時間ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）の計算を提供（calc_news_window）。
    - 銘柄バッチ処理（最大20銘柄/チャンク）、1銘柄あたりの記事最大数・文字数制限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）を実装。
    - レスポンスの厳密なバリデーションとクリッピング（_validate_and_extract）。
    - API エラー（429、ネットワーク断、タイムアウト、5xx）に対する指数バックオフとリトライ実装。失敗時は部分スキップして処理継続（フェイルセーフ）。
    - DuckDB 互換性考慮（executemany に空リストを渡さない等）。
    - score_news により ai_scores テーブルへ冪等的に書き込む（DELETE→INSERT の手順で部分失敗時の既存データ保護）。
    - テスト容易性のため OpenAI 呼び出し部分を差し替え可能（_call_openai_api をパッチ可能）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動ETF）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - マクロニュース抽出は news_nlp.calc_news_window と重複しない独立実装で行い、モジュール結合を低減。
    - OpenAI 呼び出しに対するリトライ・フォールバック（失敗時 macro_sentiment=0.0）や JSON パース保護を実装。
    - 計算結果は market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）。
    - ルックアヘッドバイアス防止（target_date 未満のデータのみを参照、date.today() を直接参照しない等）。

- リサーチ機能（kabusys.research）
  - ファクター計算（factor_research）
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR、相対 ATR、平均売買代金、出来高比）、Value（PER, ROE）を DuckDB 上で SQL によって計算。
    - データ不足時は None を返す設計で安全に動作。
    - calc_momentum / calc_volatility / calc_value を提供し、(date, code) をキーとする辞書リストを返却。
  - 特徴量解析ユーティリティ（feature_exploration）
    - 将来リターン計算（calc_forward_returns: 複数ホライズン対応、入力検証あり）。
    - IC（Information Coefficient）計算（calc_ic: スピアマンのランク相関を実装、少数サンプルは None を返す）。
    - ランク変換ユーティリティ（rank: 同順位は平均ランクを採用）。
    - ファクター統計サマリー（factor_summary: count/mean/std/min/max/median を計算）。
  - 研究用ユーティリティは外部ライブラリに依存せず標準ライブラリ + DuckDB で実装。

Other notable design & quality points
- ルックアヘッドバイアス防止を各所で重視（target_date 未満のデータのみ参照、date.today()/datetime.today() の直接参照を避ける）。
- OpenAI（LLM）連携は JSON Mode を前提に厳密パース・堅牢なフォールバックを実装。
- API 呼び出しに関してはテストフレンドリー（呼び出し関数をパッチしてモック可能）。
- DB 書き込みは冪等性を考慮（DELETE→INSERT、ON CONFLICT 設計に言及）し、トランザクションと ROLLBACK の扱いを実装。
- ロギングを適切に挿入（info/debug/warning/exception）し、失敗時の情報を出力。
- DuckDB のバージョン差異（executemany の空リスト）や返却型（date 型の変換）に対する互換性処理を導入。
- 設定値や API キーの未設定は ValueError 等で早期検出する設計。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated / Removed / Security
- 初回リリースのため該当なし。

脚注（開発者向けメモ）
- OpenAI のモデルや API の振る舞いは今後の SDK 更新で変わる可能性があるため、_call_openai_api の切り替えやエラーハンドリングの追加拡張を想定。
- ETL / カレンダー更新 / AI スコアリングはバッチ運用を想定しており、運用時の監視・再実行戦略の整備を推奨。