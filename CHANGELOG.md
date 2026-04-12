Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。  

[0.1.0] - 2026-04-12
-------------------

Added
- 初期パブリッシュ: KabuSys 「日本株自動売買システム」基盤を実装。
  - パッケージバージョンを __version__ = "0.1.0" として公開。
- 実行/監視スクリプト
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - 環境 (KABUSYS_ENV) が paper_trading の場合は paper_trading 専用 SQLite を使用し、本番 DB と完全分離して動作。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository/OrderManager、RiskManager、Reconciler を組み立てて ExecutionEngine を実行。
    - プロセス優先度を起動時に設定（高優先度）。
    - duckdb 接続を利用して分析用 DB と連携。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。不正値はデフォルトへフォールバックして警告出力。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
    - プロセス優先度設定、DB 初期化（監視用テーブルの冪等な作成）、DuckDB 接続の確立・クローズを実装。
- 設定管理 (kabusys.config)
  - .env 自動読み込み機能（プロジェクトルートを .git または pyproject.toml から検出）。
  - 読み込み優先度: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動読み込み無効化対応（テスト等で利用）。
  - .env パーサの強化: export プレフィックス、クォート文字列中のバックスラッシュエスケープ、インラインコメントの扱いなどに対応。
  - 必須環境変数検査ヘルパー（_require）。
  - 各種設定プロパティを提供（DB パス、PID ファイル、kill flag、閾値、環境種別判定、ログレベル等）。
  - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder: 候補選定 select_candidates、等金額 calc_equal_weights、スコア加重 calc_score_weights を実装。
  - risk_adjustment: セクター集中制限 apply_sector_cap、レジーム乗数 calc_regime_multiplier を実装。セクターが unknown の扱い、レジーム未定義時のフォールバック挙動を明示。
  - position_sizing: 各銘柄の発注株数を計算する calc_position_sizes を実装。risk_based/equal/score の配分方式、lot_size（単元）丸め、aggregate cap（cash に対するスケーリング）、cost_buffer による保守見積り、残差処理ロジックを含む。
- 研究・ファクター計算（kabusys.research）
  - factor_research: モメンタム / ボラティリティ / バリュー系ファクター計算を実装（DuckDB を利用して prices_daily, raw_financials を参照）。
    - モメンタム: mom_1m / mom_3m / mom_6m / ma200_dev（200日 MA の乖離）等。
    - ボラティリティ: ATR（20 日）や 20 日平均売買代金、出来高比率等。
    - バリュー: PER / ROE（target_date 以前の最新財務データを結合）。
  - feature_exploration: 将来リターン calc_forward_returns、IC（スピアマン順位相関） calc_ic、ランク付けユーティリティ、factor_summary（基本統計量）を実装。外部ライブラリ非依存で純粋 Python 実装。
  - research パッケージのエクスポートに zscore_normalize（kabusys.data.stats から）を含める。
- AI ニュース NLP（kabusys.ai.news_nlp）
  - raw_news を OpenAI（gpt-4o-mini）へバッチ送信して銘柄別センチメント ai_scores に書き込む機能を実装。
  - 処理仕様:
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）内の記事を対象に集約。
    - 1 銘柄あたり最大記事数／文字数でトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - 最大 _BATCH_SIZE=20 銘柄でのバッチ送信、JSON Mode を期待するプロンプト（SYSTEM_PROMPT）。
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ（最大 _MAX_RETRIES）。
    - レスポンス検証、スコアの ±1.0 クリップ、部分成功時のテーブル更新保護（対象 code のみ置換）を実装。
  - OpenAI API キーは引数または環境変数 OPENAI_API_KEY から取得。未設定時は ValueError を送出。
- ユーティリティ（kabusys.utils）
  - process_priority: Windows / POSIX（Linux, Darwin, FreeBSD）に対応したプロセス優先度設定（high/normal/low）を実装。CPU affinity 設定ユーティリティも提供。
  - 権限不足や未対応環境では警告を出して安全にスキップする設計。
- ツール（kabusys.tools）
  - paper_verification_report: Paper Trading 用 SQLite データを解析して検証レポートを生成する CLI ツールを追加。
    - 日付フィルタオプション (--from / --to)、--db で DB パス指定可能（優先度: --db > 環境変数 > デフォルト）。
    - 指標: 稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（avg/max/P95）等。
    - PASS/FAIL 判定基準と閾値（稼働率 99%、成功率 90% など）を定義。

Changed
- .env の読み込みロジックを改善し、配布後のパッケージ配置でも __file__ を起点にプロジェクトルートを探索するようにした（CWD に依存しない）。
- Settings 側で環境値（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）に対する入力検証を導入し、無効な値は ValueError で早期に通知。

Fixed
- 環境ファイルの読み込み失敗時に例外破壊せず warnings.warn による通知に変更（読み込み失敗がアプリ全体を停止させない）。
- process_priority / set_cpu_affinity での権限不足や未対応プラットフォームによる例外をキャッチして警告を出すようにし、安全に続行するように改善。
- run_monitoring の MONITOR_POLL_INTERVAL に不正な値が設定された場合に ValueError を発生させず、デフォルトへフォールバックするように修正（ログ出力あり）。

Documentation
- 各モジュールに docstring と処理手順・設計方針の注釈を充実させ、関数引数・返り値・例外・設計上の注意点（フォールバック挙動や制約）を明記。

Notes
- Monitoring は設計上、KABUSYS_ENV にかかわらず本番 sqlite_path を使うため、ローカルテスト時は注意が必要。Paper Trading の実行は run_execution が paper_trading 用 DB を使って分離する。
- DuckDB を分析用に利用しており、ファクター計算やニュース NLP の集計に活用する。
- AI スコアリングは OpenAI API へ実際に依存する部分があるため、API キー設定とレート制限に対する運用上の注意が必要。

将来の検討事項（未実装/TODO）
- position_sizing: 銘柄ごとの lot_size を stocks マスタで持たせる等の拡張（現状は全銘柄共通の lot_size を想定）。
- apply_sector_cap: price 欠損時のフォールバック価格（前日終値や取得原価）の導入検討。
- news_nlp: 部分失敗時のより細かなロールバック/再試行戦略、及び API レスポンスの詳細ロギング改善。

Authors
- KabuSys 開発チーム（コードベース内の docstring と実装に基づき作成）

-----