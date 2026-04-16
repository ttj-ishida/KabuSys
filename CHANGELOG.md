# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」の慣例に準拠しています。

## [0.1.0] - 2026-04-16

リリース初版。日本株自動売買システム「KabuSys」のコア機能群を含む初期実装を追加しました。

### 追加
- 全体
  - パッケージ初期リリース（バージョン 0.1.0）。モジュール群を公開。
  - パッケージメタ情報: __version__ = "0.1.0" を設定。

- 実行・運用
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使用し paper_trading 用の専用 SQLite DB（デフォルト: data/paper_trading.db）に記録することで本番 DB と分離。
    - エンジン起動前に停止フラグ (data/stop_requested.flag) をチェックし、フラグが立っていれば起動を行わない。
    - ExecutionEngine を別スレッドで起動し、停止フラグ検知時に安全に停止を試みる。
    - 起動時にプロセス優先度を "high" に設定。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。
    - デフォルトポーリング間隔 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可能（不正値や 0 以下はデフォルトにフォールバック）。
    - 監視処理は環境にかかわらず本番 sqlite_path を使用する設計（監視データは本番 DB を参照）。
    - 停止フラグ検知でループ終了、KeyboardInterrupt を考慮して正常終了処理。

- 設定管理
  - config.Settings を追加。
    - .env 自動ロード機能（プロジェクトルート検出: .git または pyproject.toml に基づく）。
    - .env / .env.local の読み込み順序と上書きルール（OS 環境変数を保護）。
    - 多数の環境変数アクセスプロパティを提供（J-Quants、kabu API、LINE、DB パス、監視閾値、ログレベルなど）。
    - 入力検証: KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE の有効値検査。未設定の必須環境変数は例外を投げる _require() を実装。

- ポートフォリオ構築（純関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順選定（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（スコア合計が 0 の場合はフォールバックで等配分）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中制限の適用（当日売却候補を露出計算から除外、"unknown" セクターは制限対象外）。
    - calc_regime_multiplier: 市場レジームに応じた資金乗数（bull/neutral/bear マップ、未知レジームは警告して 1.0 でフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: 重みや候補リストを基に銘柄ごとの発注株数を算出（risk_based / equal / score の各方式をサポート）。
    - 単元株（lot_size）丸め、ポジション上限・集計上限（available_cash）に対するスケーリング、cost_buffer（手数料・スリッページ想定）考慮、残差処理による追加配分ロジックを実装。

- 研究（Research）機能
  - research.factor_research
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率（ma200_dev）を DuckDB の prices_daily から計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER・ROE を計算（target_date 以前の最新財務データを取得）。
  - research.feature_exploration
    - calc_forward_returns: 指定ホライズンの将来リターンを一括クエリで取得（デフォルト horizons=[1,5,21]）。
    - calc_ic, rank, factor_summary: IC（スピアマンランク相関）計算、ランク付け、ファクター統計要約を実装（外部ライブラリに依存せず実装）。
  - research モジュールは kabusys.data.stats の zscore_normalize と組み合わせて利用可能。

- AI / ニュース
  - ai.news_nlp
    - raw_news から銘柄別にニュースを集約し、OpenAI (gpt-4o-mini) によりセンチメントスコア（-1.0〜1.0）を生成して ai_scores テーブルへ書き込む処理を実装。
    - ニュースウィンドウ計算（target_date に対する前日 15:00 JST ～ 当日 08:30 JST の UTC 変換）を実装（calc_news_window）。
    - バッチ処理（最大銘柄数 _BATCH_SIZE=20）、記事・文字数トリム、スコアの ±1.0 クリップ、API リトライ（429/ネットワーク/5xx に対して指数バックオフ）等の設計を導入。
    - API キーの明示的解決（引数 api_key または環境変数 OPENAI_API_KEY）。未設定時は ValueError を発生させる。

- ユーティリティ
  - utils.process_priority
    - set_process_priority: Windows と POSIX（Linux/Mac/FreeBSD）差分を吸収してプロセス優先度を設定。権限不足や未対応環境では警告を出しスキップ。
    - set_cpu_affinity: カレントプロセスの CPU affinity を設定（cpu_count=None の場合は変更なし）。無効値チェックと例外処理を追加。

- ツール
  - tools.paper_verification_report: Paper Trading 検証レポート生成ツールを追加。
    - PAPER_TRADING_SQLITE_PATH (または --db) からデータを読み込み、稼働率・注文成功率・送信率・P95 レイテンシなどを算出して標準出力にレポートを出力。
    - 判定基準（閾値）:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - P95 計算、日付フィルタ、各種 SQL クエリ実装。DB が存在しない場合のエラーメッセージを用意。

### 変更（設計上の決定／注意事項）
- DB の取り扱い
  - 監視（run_monitoring）は環境に関わらず本番 sqlite_path を使用する設計になっているため、監視用データは paper_trading と分離されない点に注意。
  - Execution エンジンは paper_trading 環境時に専用 DB を使うよう分離を行う（settings.is_paper をチェック）。

- 環境変数の自動ロード
  - プロジェクトルートの自動検出を行い .env / .env.local を読み込む。OS 環境変数は保護され、.env.local は .env を上書きする（ただし OS 環境変数を上書きしない）。

- ロギング・優先度
  - 実行スクリプトは起動時にプロセス優先度を "high" に設定する試みを行う（権限がない環境では警告が出る）。

- API 呼び出し（OpenAI）
  - ニュース NLP は API 失敗時に個別チャンクをスキップして継続するフェイルセーフ設計。部分的に書き換える方法（DELETE → INSERT の限定的適用）で一部失敗時に全体を壊さない設計を想定。

### 修正（バグ修正 / 安全弁）
- 環境変数パーサ
  - .env パース時に export プレフィックス・クォート文字列（エスケープ処理含む）・インラインコメントなどを正しく処理する実装を導入し、より堅牢に読み込みを行うよう改善。

- MONITOR_POLL_INTERVAL の取り扱い
  - 不正または 0/負値が与えられた場合にデフォルトへフォールバックするロジックを実装（time.sleep に渡せない値を防止）。

- DuckDB / SQLite のクエリ
  - 各種研究・集計関数で NULL 値やデータ不足に対する扱いを明示的に実装（例: cnt_200 / cnt_atr による閾値判定、latency の NULL フィルタなど）。

- ポジションサイズ算出
  - 集計上限超過時のスケーリングと lot_size 単位での丸め処理、および端数扱いでの再配分ロジックを実装して安全にキャッシュ配分を行うように改善。

### 既知の問題 / 制約
- ai.news_nlp の一部処理（記事取得・チャンク送信以降の完全な実装やテーブル書き込みロジックの詳細）は継続作業対象（このリリースで基本設計と一部処理を追加）。
- price_map に価格が欠損（0.0）だった場合、apply_sector_cap によるエクスポージャーが過少推定されてしまう可能性あり（TODO: 前日終値や取得原価でのフォールバックを検討）。
- set_cpu_affinity はプラットフォーム依存で権限不足や未サポート環境で失敗する可能性があるが、失敗時は警告を出して処理を継続する。

### セキュリティ
- OpenAI API キーは環境変数 OPENAI_API_KEY または関数引数で明示的に渡す必要がある。自動的なキーの埋め込み等は行わない。
- .env の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト等での安全策）。

---

今後の予定:
- ai.news_nlp の完全実装（バッチ送信・レスポンス検証・DB への安全な反映）。
- モニタリング・実行エンジン周りの追加テストと運用稼働検証。
- portfolio/position_sizing の銘柄別 lot_size 対応（マスタ連携）。
- 追加メトリクス・可観測性向上（詳細ログ、Prometheus などの統合検討）。