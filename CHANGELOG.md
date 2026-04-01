# Changelog

すべての重要な変更点をこのファイルに記録します。本ファイルは「Keep a Changelog」形式に準拠しています。  
リリースはセマンティックバージョニング (MAJOR.MINOR.PATCH) を使用します。

## [Unreleased]

## [0.1.0] - 2026-04-01
### Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージメタ情報:
    - src/kabusys/__init__.py に __version__ = "0.1.0" を設定し、公開モジュールとして "data", "strategy", "execution", "monitoring" を定義。

- 環境変数 / 設定管理
  - src/kabusys/config.py
    - .env / .env.local ファイルと OS 環境変数から設定を自動ロードする実装を追加。
    - プロジェクトルートの自動検出ロジックを導入（.git または pyproject.toml を起点に探索）。パッケージ配布後でも CWD に依存せずに動作。
    - .env パーサ実装: export プレフィックス対応、クォート（シングル/ダブル）のエスケープ処理、インラインコメント判定などをサポート。
    - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / システム環境（KABUSYS_ENV, LOG_LEVEL）などをプロパティとして安全に取得。必須設定は未設定時に ValueError を送出。
    - 有効な KABUSYS_ENV 値（development, paper_trading, live）やログレベルチェックを実装。

- AI ニュース NLP（銘柄別センチメント）
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を集約して銘柄ごとのニューステキストを構築し、OpenAI（gpt-4o-mini）を使ってセンチメントを -1.0〜1.0 にスコア化。
    - 時間ウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST）を提供する calc_news_window を実装。
    - バッチ処理（最大 20 銘柄／API 呼び出し）・1 銘柄あたり記事数・文字数制限（トリム）を実装し、トークン肥大化に対処。
    - レスポンス検証ロジックを実装（JSON の抽出・バリデーション、未知コードの無視、スコアの数値検証、±1.0 クリップ）。
    - レート制限・タイムアウト・ネットワーク断・5xx に対する指数バックオフリトライを実装。致命的ではない場合はスキップして継続（フェイルセーフ）。
    - DuckDB の executemany に関する互換性考慮（空パラメータを渡さないガード）を実装。
    - 公開関数 score_news(conn, target_date, api_key=None) を提供し、取得したスコアを ai_scores テーブルへ冪等的に書き込む（DELETE → INSERT）。

- 市場レジーム判定
  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定する score_regime を実装。
    - マクロセンチメントは raw_news からマクロキーワードでフィルタしたタイトルを OpenAI（gpt-4o-mini）で評価。
    - LLM 呼び出しはリトライ・エラー処理を行い、API 失敗時は macro_sentiment=0.0 にフォールバックする安全設計。
    - データベースへの書き込みはトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等性を確保。失敗時は ROLLBACK を試みる。

- Data（ETL / カレンダー管理 / パイプライン）
  - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py
    - ETL の公開インターフェース ETLResult を実装（取得件数、保存件数、品質チェック結果、エラー一覧を含む dataclass）。
    - 差分更新・バックフィル・品質チェックの設計を反映するパイプライン用ユーティリティを備える（詳細は doc-like コメント）。
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理（market_calendar テーブル）実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。DB にカレンダー情報がない場合は曜日ベース（週末除外）でフォールバック。
    - calendar_update_job により J-Quants API から差分取得し、バックフィルと健全性チェック（最大未来日数）を行い冪等保存を実行。
    - DB の欠損や NULL 値に対するログ出力とフォールバックロジックを実装。

- Research（ファクター計算・特徴量探索）
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER, ROE）を計算する関数を実装:
      - calc_momentum(conn, target_date)
      - calc_volatility(conn, target_date)
      - calc_value(conn, target_date)
    - DuckDB SQL を用いた実装で、prices_daily / raw_financials のみを参照。データ不足時は None を返す設計。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン算出 calc_forward_returns(conn, target_date, horizons=None)
    - IC（Spearman の ρ）算出 calc_ic(...)
    - ランク変換ユーティリティ rank(values)
    - ファクター統計サマリー factor_summary(records, columns)
    - pandas 等に依存しない純 Python 実装を採用。
  - src/kabusys/research/__init__.py で上記関数を公開（および data.stats の zscore_normalize を再エクスポート）。

- その他ユーティリティ
  - src/kabusys/ai/__init__.py で score_news をエクスポート。
  - DuckDB を前提としたクエリ実装と、テスト容易性のために OpenAI 呼び出し箇所に差し替え可能な設計（ユニットテストでの patch を想定）。

### Changed
- 初期リリースのため該当なし。

### Fixed
- 初期リリースのため該当なし。

### Security
- 初期リリースのため該当なし。

### Notes / 備考
- 必須環境変数:
  - OPENAI_API_KEY（AI 機能呼び出し時に必要、関数引数で上書き可能）
  - JQUANTS_REFRESH_TOKEN（J-Quants API）
  - KABU_API_PASSWORD（kabu ステーション接続）
  - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（Slack 通知）
- .env 自動ロード:
  - プロジェクトルートの .env と .env.local を、OS 環境変数を保護しつつ自動ロードします（.env.local は .env を上書き）。
  - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB 注意点:
  - DuckDB バージョン差異に対応するため executemany に空リストを渡さないようガードを実装しています。DB 操作を呼ぶ際は空リスト処理に注意してください。
- フェイルセーフ設計:
  - LLM/API の失敗は多くの場合にフォールバック（0.0 やスキップ）して全処理を止めない設計です。これは実運用での堅牢性を意図したものです。
- ルックアヘッドバイアス回避:
  - すべての分析関数は内部で datetime.today()/date.today() を直接参照せず、明示的に渡された target_date に依存する設計になっています。

---

今後のリリース案としては以下を検討しています:
- strategy / execution / monitoring モジュールの実装と公開 API の追加
- テストカバレッジ強化（OpenAI 呼び出しのモックを含む）
- パフォーマンス改善（大規模データ処理のためのストリーミングや並列化）
- ドキュメント（README, API リファレンス、セットアップ手順）の拡充

もし CHANGELOG に追加してほしい詳細（例: 各関数の戻り値例、既知の制約、リリース手順など）があれば教えてください。