Keep a Changelog に準拠した変更履歴（日本語）
全ての重要な変更はここに記載します。SemVer に従いバージョンを付与しています。

## [0.1.0] - 2026-04-12
初期リリース。本リポジトリに含まれる主要機能・改善点・既知の制約をまとめます。

### 追加 (Added)
- 実行エントリ
  - run_execution.py: ExecutionEngine を起動する CLI エントリポイントを追加。  
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、paper_trading 用の SQLite（既定: data/paper_trading.db）に記録することで本番 DB と分離。
    - 起動時にプロセス優先度を設定するユーティリティを呼び出す。
    - duckdb/SQLite の接続確立とリソースクローズ処理を実装。
- 監視エントリ
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト: 60 秒）。不正な値はデフォルトにフォールバック。
    - 監視は環境に関わらず本番 sqlite_path を使用して監視テーブルを記録。
- 設定管理
  - config.py: .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）と安全な読み込みロジックを実装。  
    - .env / .env.local の読み込み順序、.env.local の上書き挙動、OS 環境変数の保護（protected キー）に対応。
    - export KEY=val、引用符付き値、インラインコメント等の .env 文法をサポートするパーサを実装。
    - Settings クラスを追加し、環境変数の取得・バリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）・パスの Path 化を提供。
- ポートフォリオ構築 (Portfolio)
  - portfolio/portfolio_builder.py:
    - 候補選定（スコア降順 + タイブレーク）、等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights を実装。スコアが全て 0 の場合は等金額にフォールバック。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限（max_sector_pct）を満たすための候補フィルタリング。
    - calc_regime_multiplier: マーケットレジームに応じた投下資金乗数（bull/neutral/bear）を提供。未知レジームは警告のうえ 1.0 でフォールバック。
  - portfolio/position_sizing.py:
    - calc_position_sizes: risk_based / equal / score の各配分方式に対応。単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash）に対するスケーリング、cost_buffer（手数料・スリッページ想定）を実装。スケーリング時の remainder を用いた再配分ロジックも実装。
- リサーチ機能 (Research)
  - research/factor_research.py:
    - calc_momentum, calc_volatility, calc_value を実装。DuckDB 接続を受け取り、prices_daily / raw_financials テーブルから純粋関数的にファクターを計算。
    - 200 日移動平均、ATR、出来高/売買代金平均などをサポート。十分な履歴が無い場合は None を返す設計。
  - research/feature_exploration.py:
    - calc_forward_returns（任意ホライズンでの将来リターン取得）、calc_ic（Spearman ランク相関による IC 計算）、factor_summary（基本統計量）、rank（同位の平均ランク処理）を実装。pandas 等に依存しない純粋 Python 実装。
  - research/__init__.py: 外部公開 API を整備（zscore_normalize の re-export を含む）。
- AI / ニュース NLP
  - ai/news_nlp.py:
    - raw_news を OpenAI（gpt-4o-mini）でセンチメント解析して ai_scores に書き込む score_news を実装。
    - 前日 15:00 JST 〜 当日 08:30 JST のウィンドウ計算。記事集約、銘柄ごとの文字数制限・記事数制限（トリム）、20 銘柄／バッチ制御、JSON Mode レスポンスのバリデーション、スコアの ±1.0 クリップ、429/ネットワーク/5xx に対する指数バックオフリトライを実装。
    - API キーは引数または環境変数 OPENAI_API_KEY から取得。未設定時は ValueError。
- ツール
  - tools/paper_verification_report.py:
    - Paper Trading の検証レポート生成 CLI を追加。PAPER_TRADING_SQLITE_PATH を参照または --db で指定可能。
    - 稼働率、注文成功率（fill rate）、送信率、P95 レイテンシなどの指標を集計し、閾値（デフォルト）に基づく PASS/FAIL 判定を出力。P95 計算、日付フィルタ、DB 存在チェックを実装。
- ユーティリティ
  - utils/process_priority.py:
    - Windows / POSIX（Linux, Darwin, FreeBSD）に対応したプロセス優先度設定（高/普通/低）を実装。psutil を利用し、アクセス拒否や未実装例外を警告でハンドリング。
    - set_cpu_affinity: プロセスを先頭 N コアに固定する機能を追加（引数 None で無効化、1 未満は ValueError）。
- パッケージメタ
  - __init__.py: __version__ = "0.1.0" を設定。
  - パッケージの public API を __all__ で整理（portfolio / research 等）。

### 変更 (Changed)
- 設計上の方針や実装ノートをコード内ドキュメントに明記:
  - research, portfolio 等の関数群は「DB 参照は限定」「純粋関数」「外部 API へはアクセスしない」などの設計方針を明確化。
  - .env 自動読み込みはプロジェクトルートが検出できない場合はスキップする安全設計。
  - Paper Trading と本番 DB を明確に分離（デフォルトパスと環境変数で制御）。
  - DuckDB を分析用途、SQLite をトランザクション／ログ用途に使い分ける方針。

### 修正 (Fixed)
- .env パーサ:
  - export プレフィックス、引用符付き値、バックスラッシュエスケープ、インラインコメントの解釈など実務でよくあるケースに対応。これにより .env の読み込みでの誤読を低減。
- ポジションサイズ算出:
  - aggregate cap 超過時のスケールダウンロジックで lot_size 単位の端数処理と残余配分を実装し、投資総額が available_cash を超えないよう保守的に調整。
- process_priority:
  - サポートされていない OS 上では優先度設定をスキップし、エラーや例外は警告ログに変換することで起動失敗を防止。
- AI ニュース処理:
  - API レスポンスの完全性チェックとスコア型検証を実装し、不正なレスポンスでのテーブル汚染を防止。部分失敗時に既存スコアを保護するため、対象 code を絞って置換（DELETE + INSERT）する方針。

### 注意 / 既知の制約 (Known issues / Notes)
- sector_exposure 計算で price が欠損（0.0）の場合、エクスポージャーが過少見積りされてセクター制限が適切に働かない可能性がある。将来的には前日終値や取得原価でのフォールバックを検討中（コード内に TODO コメントあり）。
- position_sizing は現状全銘柄で単一の lot_size（デフォルト 100）を想定。将来的には銘柄別 lot_map を受け取る設計へ拡張予定（TODO コメントあり）。
- DuckDB に対する executemany の制約を考慮し、空の params を渡さないよう注意している実装箇所がある（ai/news_nlp の書き込み等）。
- ai/news_nlp の OpenAI 呼び出しはネットワーク/API 側の制約に依存するため、レート制限やコスト管理が必要。
- calc_ic は有効レコードが 3 件未満の場合 None を返す（実務上のサンプル数不足に対する保護）。
- .env 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用途想定）。

### セキュリティ (Security)
- .env の自動読み込み時、既存の OS 環境変数は protected として上書きされない設計。明示的に .env.local での上書きを許可するが保護されたキーは除外されるため、意図しない環境変数の上書きを防止。
- OpenAI API キーや各種シークレットは Settings 経由で環境変数から取得する仕様。キー未設定時は明示的にエラーを出す（fail-fast）。

---

注: 本 CHANGELOG はソースコードの内容から推測して作成しています。実際のリリースノートとして使う場合は、コミット履歴やリリース記録と照合して調整してください。