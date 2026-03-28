KEEP A CHANGELOG
=================

すべての重要な変更をこのファイルに記録します。本プロジェクトは "Keep a Changelog" の規約に従います。

[Unreleased]
-----------

- なし

[0.1.0] - 2026-03-28
-------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - src/kabusys/__init__.py による公開 API: data, strategy, execution, monitoring。

- 環境変数・設定管理
  - src/kabusys/config.py
    - .env/.env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を探索して決定）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - .env パーサは export 形式・クォート（シングル/ダブル）・バックスラッシュエスケープ・インラインコメント処理を考慮。
    - 環境変数上書き時に OS 環境変数を保護する protected 機構を実装。
    - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 環境（development/paper_trading/live）/ログレベルの取得と検証を行う。

- AI（NLP）機能
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）の JSON Mode で銘柄別センチメント（-1.0〜1.0）を算出、ai_scores テーブルへ書き込む機能 score_news を実装。
    - 前日 15:00 JST ～ 当日 08:30 JST のウィンドウ計算（UTC 変換）を実装（calc_news_window）。
    - 1銘柄当たりの記事数/文字数制限（チャンク化・トリム）と、最大 BATCH サイズによるバッチ送信。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ。
    - レスポンスの堅牢なバリデーションと JSON 抽出ロジック（余分な前後テキストの除去、results 構造検査）。
    - スコアを ±1.0 にクリップ。部分失敗時に既存スコアを消さない（対象コードのみ DELETE → INSERT）。
    - テスト容易性のため _call_openai_api を patch で差し替え可能に実装。

  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）と、news_nlp によるマクロセンチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
    - MA 計算でルックアヘッドバイアスを防ぐため target_date 未満のデータのみ使用、データ不足時には中立 (ma200_ratio=1.0) を採用。
    - マクロニュース抽出はキーワードベース。記事がない場合は LLM 呼び出しをスキップして macro_sentiment=0.0。
    - OpenAI 呼び出しでのリトライ・エラー処理・JSON パース失敗時のフォールバック（macro_sentiment=0.0）。
    - market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実施。
    - テスト用差し替えポイントを用意（_call_openai_api は news_nlp とは別実装）。

- リサーチ / ファクター計算
  - src/kabusys/research/factor_research.py
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算（データ不足は None）。
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務データを取得して PER / ROE を算出。
    - DuckDB を用いた SQL ベース実装。営業日・ウィンドウバッファ設計で週末/祝日を吸収。
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: 指定 horizon の将来リターンを計算（horizons の妥当性検査あり）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を算出、データ不足時は None。
    - rank: 同順位は平均ランクを返す実装（丸めで ties の誤検出を防止）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリ機能。
  - research パッケージの __all__ に主要関数をエクスポート。

- データプラットフォーム / カレンダー / ETL
  - src/kabusys/data/calendar_management.py
    - market_calendar を用いた営業日判定ロジックを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB にデータがない場合は曜日ベース（週末除外）でフォールバックする一貫性のある設計。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等更新（バックフィル、健全性チェックを含む）。
  - src/kabusys/data/pipeline.py
    - ETL パイプラインのユーティリティ（差分取得、保存、品質チェックの枠組み）を実装。
    - ETLResult dataclass により ETL 実行結果（取得数、保存数、品質問題、エラー等）を集約し to_dict を提供。
    - DuckDB テーブル存在チェックや最大日付取得などの内部ユーティリティを実装。
  - src/kabusys/data/etl.py
    - ETLResult を再エクスポートして公開インターフェースを簡潔化。

- DuckDB / 互換性改善
  - executemany に空リストを渡せない DuckDB の制約を考慮して空チェックを実装。
  - リスト型バインドが不安定なため、DELETE の際に executemany で個別 DELETE を行う等の互換性対策を実施。
  - 日付はすべて datetime.date を使い、UTC naive datetime を明示的に扱うことで timezone 混入を防止。

- 品質・安全・運用面
  - ルックアヘッドバイアス防止のため、AI スコアリング・レジーム評価処理では datetime.today()/date.today() を参照しない設計。
  - OpenAI 呼び出しの失敗は例外にせずフェイルセーフなデフォルト（0.0）で継続する箇所がある（可用性優先）。
  - ロギングを各モジュールに組み込み、問題時は警告/例外ログを出力する設計。
  - テスト容易性のため外部 API 呼び出しポイントを差し替え可能に実装（ユニットテスト用の patch を想定）。

Changed
- N/A（初期リリースのため変更履歴なし）

Fixed
- N/A（初期リリースのため修正履歴なし）

Removed
- N/A（初期リリースのため削除履歴なし）

Notes / Usage tips
- 環境変数:
  - OpenAI を利用する関数（score_news, score_regime）は引数 api_key を受け取り、未指定時は環境変数 OPENAI_API_KEY を使用する。空文字列は未設定と扱われる。
  - 自動 .env 読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - .env 読み込み順は .env（既存環境未設定のキーのみ）→ .env.local（上書き可能）です。
- テスト:
  - OpenAI 呼び出しは各モジュール内の _call_openai_api を patch して差し替え可能。ユニットテストでのモック注入が容易。
- DuckDB:
  - executemany の空リスト渡し不可等の制約に対応済み。DuckDB バージョン依存の挙動に注意。

References
- この CHANGELOG はコードベース（src/ 以下）から設計意図・公開 API・副作用を推測して作成しています。実際のリリースノートはリリース手順や CI/CD に合わせて適宜更新してください。