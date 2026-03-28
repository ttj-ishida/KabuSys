# Changelog

すべての重要な変更はこのファイルに記録します。  
この変更履歴は "Keep a Changelog" のフォーマットに準拠しています。

フォーマットの方針:
- バージョンごとに主要な追加・変更・修正点を列挙しています。
- 各項目はコードベース（src/kabusys 以下）の実装内容から推測して記載しています。

該当バージョン:
- Unreleased: 今後の変更予定や軽微な改善メモ
- [0.1.0] - 2026-03-28: 初期公開リリース（コードベースに基づく初期実装）

---

## [Unreleased]

### Added
- テストや運用で便利なフックや堅牢性のさらに小さな改善を予定（例: OpenAI API 呼び出しのモック差し替えポイントへの追加、ログ改善、エラーメッセージの詳細化など）。
- ドキュメントや型アノテーションの補強（必要に応じて）。

### Changed
- 小さな内部実装のリファクタ（ロギング粒度、例外メッセージの改善等）を想定。

### Fixed
- API 呼び出し/DB 周りのエッジケース対処（実運用で見つかったら都度追加予定）。

---

## [0.1.0] - 2026-03-28

初期リリース。日本株の自動売買・データ基盤・リサーチ・AI スコアリングを構成するコアモジュール群を実装。

### Added
- パッケージ基礎
  - kabusys パッケージの初期公開 (src/kabusys/__init__.py)。バージョン `0.1.0` を設定し、主要サブパッケージ（data, strategy, execution, monitoring）を公開。

- 設定/環境変数管理
  - .env/.env.local 自動読み込み機能を実装（src/kabusys/config.py）。
    - プロジェクトルート検出は .git または pyproject.toml を基準に行うため、CWD 非依存。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート（テスト用）。
  - .env のパース機能強化:
    - export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理を考慮。
  - Settings クラスを提供し、アプリ向けの設定プロパティを公開:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL など。
    - env/log_level 値のバリデーション（許容値チェック）とユーティリティプロパティ（is_live/is_paper/is_dev）。

- データプラットフォーム（Data）
  - カレンダー管理モジュール（src/kabusys/data/calendar_management.py）
    - JPX カレンダー管理（market_calendar テーブル）と営業日判定ロジックを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の API を提供。
    - 夜間バッチ用 calendar_update_job 実装（J-Quants からの差分取得→冪等保存）。
    - DB が未取得の場合は曜日ベースのフォールバック（週末を非営業日）を採用。
    - 最大探索日数制限や健全性チェックを実装し無限ループ・異常値を防止。

  - ETL / パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを実装し、ETL 実行結果（取得数、保存数、品質問題、エラー）を統一的に扱う。
    - 差分取得、バックフィル、品質チェック、idempotent 保存（jquants_client 経由）を前提とした設計方針を反映。
    - DuckDB の取り扱いとテーブル存在確認ユーティリティを提供。

  - data パッケージの簡易公開インターフェース（etl の ETLResult 再エクスポート等）。

- AI（ニュース NLP / レジーム判定）
  - ニュースセンチメントスコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を元に、銘柄ごとにニュースを集約して OpenAI（gpt-4o-mini）にバッチ送信しセンチメントスコアを ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ（前日15:00 JST～当日08:30 JST）算出機能（calc_news_window）。
    - チャンク処理（最大20銘柄/チャンク）、1銘柄あたり記事数・文字数のトリム、JSON Mode レスポンスのバリデーションとスコアクリップ（±1.0）。
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ、API 呼び出し失敗時はロギングしてスキップするフェイルセーフ設計。
    - テスト用に _call_openai_api を差し替え可能（unittest.mock.patch を想定）。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日 MA 乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して、日次で market_regime テーブルへ冪等書き込み。
    - ma200_ratio 計算、マクロ記事抽出、OpenAI 呼び出し（gpt-4o-mini）の実装、API 障害時のフォールバック（macro_sentiment=0.0）。
    - DB 書き込みは BEGIN/DELETE/INSERT/COMMIT の冪等パターン。失敗時は ROLLBACK を試行して例外を伝播。
    - レジームラベルは閾値に基づく "bull"/"neutral"/"bear" を採用。

- リサーチ（Research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - モメンタム（1M/3M/6M リターン、ma200_dev）、ボラティリティ（20日 ATR、ATR%）、流動性（20日平均売買代金、出来高比率）、バリュー（PER, ROE）等の計算関数を実装。
    - DuckDB を利用した SQL + Python 実装で、prices_daily / raw_financials の参照に限定。
    - データ不足時は None を返すなどの堅牢性を実装。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns: 任意ホライズンに対応、入力バリデーションあり）。
    - IC（Information Coefficient）計算（calc_ic: スピアマンのランク相関、無効データ取り扱い）。
    - ランク変換ユーティリティ（rank）と統計サマリー（factor_summary）を実装。
  - research パッケージの公開インターフェースで主要関数を再エクスポート。

### Changed
- （初期リリースのため該当なし。実装時の設計方針や制約をコード中に記載）
  - ルックアヘッドバイアス対策として、datetime.today()/date.today() に依存しない設計を明記・実装（外部から target_date を与える設計）。
  - DuckDB のバージョン差（executemany の空リストバインド問題など）を考慮した保護ロジックを実装。

### Fixed
- フェイルセーフ挙動およびエラーハンドリング（設計上の注意点・実装）
  - OpenAI/API 周りの例外（RateLimit, 接続エラー, タイムアウト, APIError 5xx 等）に対してリトライ戦略やフォールバック値（例: macro_sentiment=0.0）を実装。
  - DB 書き込み失敗時に ROLLBACK を試行し、ROLLBACK 自体の失敗は警告ログにとどめる実装。
  - market_calendar の不完全データ（NULL）に対して警告ログを出し曜日フォールバックを使用する等の堅牢化。

### Security
- セキュリティ修正はこのバージョンでは明示的には含まない。
- 実運用では API キーやパスワード等の取り扱いに注意（Settings は必須環境変数の検証を実施）。

---

参照:
- 本 CHANGELOG の内容はソースコード（src/kabusys 以下）の docstring・コメント・実装から推測して作成しています。実際の変更履歴やリリース日付はプロジェクトのリリースノートに従って更新してください。