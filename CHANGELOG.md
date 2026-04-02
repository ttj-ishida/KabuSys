# CHANGELOG

すべての重要な変更は Keep a Changelog の形式に従って記載します。  
このファイルはユーザー向けのリリースノートであり、機能追加・変更・不具合対応・設計上の注意点などをまとめています。

フォーマット:
- 重大な変更（Added / Changed / Fixed / Deprecated / Removed / Security）ごとに項目を分けています。

## [0.1.0] - 2026-04-02

初回公開リリース。日本株自動売買システム「KabuSys」の基盤機能を実装しました。主要コンポーネントと設計方針に沿った実装を含みます。

### Added
- パッケージ基盤
  - パッケージメタ情報と公開 API の定義を追加（src/kabusys/__init__.py）。
  - バージョン: 0.1.0

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルートの検出ロジック（.git / pyproject.toml を探索）を実装し、CWD に依存しない自動ロードを実現。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト向け）。
  - 柔軟で堅牢な .env パーサー実装（export プレフィックス・シングル/ダブルクォート・エスケープ・インラインコメント等に対応）。
  - 環境設定ラッパー Settings を提供。主要プロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - PID_FILE_PATH, CPU/MEMORY/DISK しきい値
    - KABUSYS_ENV（development/paper_trading/live）および LOG_LEVEL の検証
  - 必須環境変数が未設定の場合は ValueError を投げ、ユーザーに .env.example を参照するよう案内。

- AI（自然言語処理 / レジーム判定）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news + news_symbols から銘柄ごとに記事を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄単位のセンチメント ai_score を ai_scores テーブルへ書き込み。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window として実装。
    - バッチサイズ、記事数・文字数上限、JSON Mode による厳密なレスポンス検証実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。その他はスキップして継続（フェイルセーフ）。
    - レスポンスのバリデーションと ±1.0 のクリッピング。部分成功時に既存スコアを消さないよう部分置換（DELETE → INSERT）で冪等性を確保。
    - テスト用フック: _call_openai_api はユニットテストでパッチ可能に設計。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動 ETF）の 200 日移動平均乖離（重み 70%）とマクロセンチメント（LLM、重み 30%）を組み合わせて日次で市場レジーム（bull / neutral / bear）を判定。
    - prices_daily と raw_news を参照して ma200_ratio とマクロ記事を取得。
    - OpenAI（gpt-4o-mini）を用いたマクロセンチメント評価（JSON 出力想定）。API エラー時は macro_sentiment=0.0 で継続（フェイルセーフ）。
    - 合成スコアはクリップされ、閾値によりラベル付け。market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - ルックアヘッドバイアス対策: datetime.today() を参照しない、prices_daily クエリは target_date 未満を使用。
    - テスト用フック: _call_openai_api はパッチ可能。

- リサーチ / ファクター計算（src/kabusys/research/*）
  - factor_research.py:
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率）、Value（PER、ROE）を実装。
    - DuckDB 上で SQL ウィンドウ関数を用いて効率的に計算。データ不足時は None を返す方針。
  - feature_exploration.py:
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic：Spearman の ρ 計算）、ランク変換ユーティリティ(rank)、統計サマリー（factor_summary）を実装。
    - Pandas 等に依存せず標準ライブラリと DuckDB のみで実装。
  - research パッケージのエクスポートを追加（__init__.py）。

- データ処理 / ETL / カレンダー（src/kabusys/data/*）
  - calendar_management.py:
    - JPX マーケットカレンダー管理（market_calendar）と営業日判定ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。
    - DB にカレンダーがない場合は曜日ベース（土日非営業）でフォールバック。
    - 夜間バッチ更新 job（calendar_update_job）を実装。J-Quants クライアントから差分取得し冪等保存。バックフィルと健全性チェックを実装。
  - pipeline.py:
    - ETLResult dataclass と ETL パイプラインユーティリティ（差分取得、保存、品質チェックの設計方針）を実装。
    - ETLResult.to_dict() により品質問題を辞書化して監査ログ等で使用可能。
  - etl.py: pipeline.ETLResult を再エクスポート。
  - jquants_client への参照を想定しており、fetch/save 系関数との連携を行う設計。

- テスト・運用を考慮した設計上の追加
  - API 呼び出し (_call_openai_api) をユニットテストでパッチ可能にして、外部呼出しを模擬しやすくしています。
  - DuckDB に対する executemany の空リスト回避など、実行時の互換性問題に配慮した実装。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Deprecated
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Security
- OpenAI API キーおよび各種トークン（J-Quants / Slack / Kabu API）は必須設定項目として Settings で検証。未設定の場合は早期に ValueError を発生させ、明確なメッセージを返します。
- .env 自動ロード時に OS 環境変数を保護する仕組み（protected set）を導入。

### Notes / 実装上の重要な設計判断（ユーザー・デベロッパ向け）
- ルックアヘッドバイアス対策: AI モジュール・リサーチモジュール全てで datetime.today() / date.today() を直接参照しない設計。すべて target_date を明示的に渡す API を採用しています。
- フェイルセーフ: 外部 API（OpenAI、J-Quants 等）が利用できない場合でも全体処理を停止しないように設計（一部機能はスキップ・デフォルト値で継続）。ただし重要な API キー未設定は明示的にエラーにします。
- 冪等性: DB への書き込みは可能な限り冪等（DELETE→INSERT、ON CONFLICT 等）で実装し、再実行可能性を重視しています。
- ロギングと例外管理: API エラーや DB ロールバック失敗などの状況で詳細ログを出力し、上位で適切にハンドルできるようにしています。
- DuckDB 互換性: executemany の制約など DuckDB のバージョン差分を考慮した実装を行っています。

---

今後の予定（例）
- strategy / execution / monitoring モジュールの具象実装（現在はパッケージとしてプレースホルダ）。
- テストカバレッジ拡充と CI 設定。
- J-Quants / Kabu API との接続モジュールの充実とサンプル ETL 実行スクリプト。

リリースに関するフィードバック・不具合報告・改善提案は issue を通じてお願いします。