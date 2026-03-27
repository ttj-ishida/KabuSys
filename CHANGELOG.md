# Changelog

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-03-27

### Added
- 初回リリース。日本株自動売買プラットフォーム「KabuSys」のコア機能を追加。
  - パッケージエントリポイント (src/kabusys/__init__.py) とバージョン定義を追加。
- 環境設定管理
  - src/kabusys/config.py
    - .env ファイルおよび環境変数から設定を自動ロードする仕組みを実装。
    - プロジェクトルート検出（.git または pyproject.toml を基準）により CWD に依存しない自動読み込みを実現。
    - .env のパースは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントを考慮した堅牢な処理を実装。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - 必須項目取得用の _require と Settings クラスを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
    - デフォルトの DB パス（DuckDB/SQLite）、環境（development/paper_trading/live）とログレベルのバリデーションを実装。
- AI（自然言語処理 / レジーム判定）
  - src/kabusys/ai/news_nlp.py
    - ニュース記事を銘柄ごとに集約し、OpenAI（gpt-4o-mini、JSON mode）でセンチメントを評価して ai_scores テーブルへ保存する処理を実装。
    - タイムウィンドウ計算（JST ベース→UTC 変換）と記事トリミング（最大記事数・最大文字数）を実装。
    - バッチ処理（1回最大 20 銘柄）・リトライ（429/ネットワーク/5xx に対する指数バックオフ）・レスポンスバリデーション・スコアの ±1.0 クリップを実装。
    - テスト容易性のため OpenAI 呼び出し部分を差し替え可能に設計（unittest.mock.patch に対応）。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次市場レジーム（bull/neutral/bear）を判定、market_regime テーブルへ冪等書き込みを行う処理を実装。
    - LLM 呼び出しは独立実装としモジュール結合を避ける。API 失敗時はフェイルセーフで macro_sentiment=0.0 とする。
- データプラットフォーム / ETL
  - src/kabusys/data/pipeline.py
    - ETLResult データクラス（ETL 実行結果と品質チェック情報を格納）を実装。
    - 差分取得・バックフィル・品質チェックの設計方針を実装（J-Quants クライアント連携想定）。
  - src/kabusys/data/etl.py
    - pipeline.ETLResult の公開インターフェースを再エクスポート。
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー（market_calendar）管理、営業日判定（is_trading_day、next_trading_day、prev_trading_day、get_trading_days）、SQ 判定、夜間バッチ更新ジョブ（calendar_update_job）を実装。
    - DB 未取得時の曜日ベースフォールバック、最大探索日数制限、バックフィル処理、健全性チェックなどを実装。
  - DuckDB を前提とした安全なテーブル存在チェック・日付変換ユーティリティを追加。
- リサーチ / ファクター計算
  - src/kabusys/research/factor_research.py
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR、相対 ATR、平均売買代金、出来高比率）、Value（PER, ROE）を DuckDB の prices_daily / raw_financials から計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - データ不足時の None ハンドリングやログ出力を実装。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク変換ユーティリティ（rank）、統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず標準ライブラリのみで実装。
  - src/kabusys/research/__init__.py
    - 主要関数を公開。
- 共通ユーティリティ
  - OpenAI SDK 呼び出しラッパーを各モジュールで実装し、テスト時に差し替え可能な設計を採用。
  - AI 処理・ETL・DB 書き込みは冪等性・トランザクション（BEGIN/DELETE/INSERT/COMMIT）と ROLLBACK ハンドリングを備え、失敗時にログを残す実装を採用。

### Changed
- 新規リリースのため該当なし。

### Fixed
- 新規リリースのため該当なし。

### Security
- 環境変数の自動ロード時に既存 OS 環境変数を保護（protected set）する実装を追加。これにより OS 側の設定が .env で誤って上書きされるのを防止。

### Notes / Limitations
- OpenAI を利用する機能（news_nlp, regime_detector）は API キー（OPENAI_API_KEY）が必要。api_key 引数経由で注入可能。
- news_nlp の出力は JSON Mode を期待しているが、稀に前後に余計なテキストが混ざる場合に備えた復元ロジックを実装している。
- calc_value では現時点で PBR・配当利回りは未実装。
- DuckDB の executemany に関する互換性（空パラメータ不可）を考慮した実装となっている。
- 内部では datetime.today()/date.today() への直接依存を避け、ルックアヘッドバイアスを防止する設計を採用。

---

今後のリリースでは、ドキュメントの拡充・API クライアントの具体実装（jquants_client の詳細実装や kabu ステーション連携）、監視・実行モジュールの追加を予定しています。