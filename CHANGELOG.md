CHANGELOG
=========

すべての重要な変更点をここに記録します。本ファイルは「Keep a Changelog」に準拠します。

フォーマット: https://keepachangelog.com/ja/1.0.0/

なお、パッケージバージョンは src/kabusys/__init__.py の __version__ に合わせています。

[Unreleased]
------------

- ドキュメント・テスト用に内部フックや環境変数上書き制御が整備されています（例: OpenAI 呼び出しの差し替え、KABUSYS_DISABLE_AUTO_ENV_LOAD による .env 自動ロード無効化）。
- マイナーなログ出力改善・警告文言の調整。
- 既存 API の安定性向上（リトライ・フェイルセーフの扱いを一貫化）。

[0.1.0] - 2026-03-29
-------------------

Added
- パッケージ初期リリース: KabuSys — 日本株自動売買システムの基盤実装を追加。
  - パッケージメタ: src/kabusys/__init__.py にて __version__="0.1.0" を設定。
- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルと OS 環境変数から設定を読み込む自動ローダを実装。
  - プロジェクトルート検出は __file__ を起点に .git / pyproject.toml を探索するため、CWD に依存しない実装。
  - .env パース機能を強化: export プレフィックス対応、シングル/ダブルクォート内でのバックスラッシュエスケープ、インラインコメント処理。
  - 自動ロード優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - 必須環境変数チェック用の _require、Settings クラスを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
  - DB パスのデフォルト（DuckDB: data/kabusys.duckdb、SQLite: data/monitoring.db）と環境での上書き対応。
  - 環境 (KABUSYS_ENV) およびログレベル (LOG_LEVEL) の検証ロジックを実装。

- AI（自然言語処理）機能 (src/kabusys/ai)
  - ニュースセンチメントスコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news / news_symbols を集約して銘柄ごとのニューステキストを作成し、OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信してセンチメントスコアを算出。
    - バッチサイズ、記事数・文字数トリム、JSON レスポンスの厳密バリデーション、スコアの ±1.0 クリップを実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。
    - DuckDB への書き込みは、部分失敗を避けるため「対象コードのみ」DELETE → INSERT の形で冪等に実行。
    - テスト容易性のため OpenAI 呼び出し部分を差し替え可能（_call_openai_api を patch 可能）。
    - タイムウィンドウ（JST 前日 15:00 ～ 当日 08:30 を UTC に変換）を厳密に扱い、ルックアヘッドバイアスを防止。

  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - マクロ記事抽出用キーワード群、LLM のシステムプロンプト、スコア合成ロジック、閾値を実装。
    - OpenAI 呼び出しは retry/backoff を取り入れ、API 失敗時は macro_sentiment=0.0 にフォールバックして継続（フェイルセーフ）。
    - DB への書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等処理。失敗時は ROLLBACK を試行して例外を上位へ伝播。

- データ基盤ユーティリティ (src/kabusys/data)
  - マーケットカレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar を参照した営業日判定とフォールバックロジック（DB にデータが無い場合は曜日ベース）。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - calendar_update_job による J-Quants からの差分取得 → 保存ロジック（バックフィル・健全性チェック含む）。
  - ETL パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラスを公開（取得数・保存数・品質チェック結果・エラー一覧を集約）。
    - 差分更新・バックフィル・品質チェックの設計を反映したユーティリティ関数群（jquants_client, quality モジュールと連携想定）。
    - DuckDB テーブル存在チェック、最大取得日取得などの補助関数を実装。
  - その他
    - jquants_client との連携ポイントを想定（fetch/save 系関数を利用）。

- リサーチ / ファクター計算 (src/kabusys/research)
  - factor_research.py
    - Momentum (1M/3M/6M リターン、200日 MA 乖離)、Volatility (20日 ATR 等)、Value (PER/ROE) 等の計算関数を実装。
    - DuckDB 上で SQL を用いて効率的に計算。データ不足時は None を返す設計。
  - feature_exploration.py
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）、IC（Spearman ランク相関）、rank、factor_summary（基本統計量）を実装。
    - pandas 等の外部ライブラリに依存せず純粋 Python + DuckDB で完結。
  - research パッケージの __all__ を整備してユーティリティを公開。

Changed
- 初期設計時点で「ルックアヘッドバイアス防止」を徹底:
  - target_date に対する処理で datetime.today()/date.today() を直接参照しない設計（全て明示引数または ETL スケジューラ側で日付を渡す想定）。
  - prices_daily 等のクエリは target_date より前（または指定範囲内）のデータのみを使用。

Fixed
- DuckDB 互換性対策:
  - DuckDB 0.10 の executemany に空リストを渡すとエラーになる問題を回避するため、空時は executemany を呼ばないガードを追加（news_nlp.score_news 等）。
- レスポンスパースや API エラー時の堅牢性強化:
  - OpenAI レスポンスの JSON モードでも前後に余計なテキストが混入するケースに対して最外の {} を抽出して復元する処理を追加。
  - OpenAI SDK の APIError に対しては getattr による status_code 参照で将来の SDK 変更に耐性を持たせた処理を実装。
- NULL / 欠測データの扱いとログ出力を明確化:
  - market_calendar の is_trading_day が NULL の場合に警告ログを出し、曜日ベースのフォールバックを行うようにした。

Security
- 本フェーズでは特段のセキュリティ修正は含まれません。環境変数に API キー等の機密情報を置く運用を前提としています（.env / OS 環境変数）。実運用時は Secrets 管理推奨。

Notes / 実装上の設計方針（抜粋）
- API 呼び出しは冪等性・フォールバックを重視。LLM/API の一時障害時は影響を局所化して処理を継続する設計。
- DuckDB を主要な分析 DB として利用。書き込みは部分的に保護（成功した銘柄データを消さない設計）している。
- テスト容易性を考慮し、OpenAI 呼び出し部分などは差し替え（モック）可能に実装。
- 外部依存を最小化（リサーチモジュールでは pandas を使用しない）。

Breaking Changes
- なし（初期リリースのため互換性破壊の変更履歴はありません）。

Contributing
- バグ報告・改善提案は PR / issue を通じて歓迎します。重要な変更は CHANGELOG に逐次記載します。

--- 

（補足）
- この CHANGELOG はソースコードの構成・コメント・実装から推測して作成しています。実際のリリースノートとして公開する場合は、リリース作業での追加変更・日付等を最終確認してください。