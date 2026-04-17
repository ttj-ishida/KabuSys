# CHANGELOG

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]

## [0.1.0] - 2026-04-17

初回リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。主な追加点は以下のとおりです。

### 追加
- 全体
  - パッケージ初期バージョンを `0.1.0` に設定。
  - モジュール群に対する基本的なドキュメント（モジュール／関数レベルの docstring）を整備。

- 起動スクリプト
  - `run_monitoring.py`
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトへフォールバック。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグファイル（data/stop_requested.flag）の存在検出による安全停止。
    - Monitoring は環境にかかわらず本番用の sqlite_path を使用する仕様。

  - `run_execution.py`
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を使用し paper_trading 用の専用 SQLite DB（デフォルト: data/paper_trading.db）で完全分離して動作。
    - 起動前に停止フラグを確認。スレッドで Engine を動かし、停止フラグ検知で安全に停止。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理
  - `config.py`
    - 環境変数の自動ロード機能を実装（プロジェクトルートの `.env` / `.env.local` を読み込み）。OS 環境変数を保護して上書き制御。
    - `.env` パーサーは以下に対応:
      - コメント、空行、`export KEY=val` 形式、
      - シングル/ダブルクォート内のバックスラッシュエスケープ、
      - クォートなしのインラインコメント処理（空白直前の `#` をコメントとみなす）。
    - 環境変数の必須取得ヘルパー `_require`、各種設定プロパティ（DB パス、API トークン、監視閾値、PID/フラグパス、環境判定など）を実装。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` で自動ロードを無効化可能。

- ポートフォリオ構築
  - `portfolio/portfolio_builder.py`
    - シグナル選定（スコア降順、tie-breaker: signal_rank）関数 `select_candidates` を実装。
    - 等金額配分 `calc_equal_weights`、スコア加重配分 `calc_score_weights` を実装。全スコアが 0 のときは等分配へフォールバック。

  - `portfolio/risk_adjustment.py`
    - セクター集中制限を適用する `apply_sector_cap` を実装（既存ポジションのセクターごとのエクスポージャーを算出し、上限超過セクターの新規候補を除外）。
    - 市場レジームに応じた乗数 `calc_regime_multiplier` を実装（`bull`, `neutral`, `bear` のマッピング。未知のレジームはフォールバックで 1.0）。

  - `portfolio/position_sizing.py`
    - 発注株数決定ロジック `calc_position_sizes` を実装（`risk_based` / `equal` / `score` の配分方式をサポート）。
    - 単元株（lot）丸め、1銘柄上限、合計投下上限（aggregate cap）を考慮したスケールダウンロジックを実装。
    - cost_buffer（手数料・スリッページ見積り）を加味して投資額を保守的に算出。
    - 将来的拡張箇所（銘柄別 lot_size など）は TODO コメントで明示。

  - `portfolio/__init__.py`
    - 上記関数群をパッケージ API としてエクスポート。

- モニタリング / DB 初期化
  - `monitoring.monitoring_db.init_monitoring_db` を利用する起動ルーチンを追加（起動時に監視テーブルが存在することを保証）。

- ユーティリティ
  - `utils/process_priority.py`
    - クロスプラットフォームでのプロセス優先度設定を実装（Windows: `psutil` の priority class、POSIX: nice 値）。
    - CPU affinity を最初の N コアに固定する `set_cpu_affinity` を実装（利用可能であれば）。
    - 権限不足や未対応 OS の場合は警告を出して処理をスキップするフェイルセーフ。

- リサーチ / ファクター
  - `research/factor_research.py`
    - Momentum / Volatility / Value ファクター計算関数を実装（DuckDB 接続を受け prices_daily/raw_financials を参照して計算）。
    - 各関数はデータ不足時に None を返すなど堅牢化。
    - 大規模スキャンを見越した日数バッファとウィンドウ管理を導入。

  - `research/feature_exploration.py`
    - 将来リターン計算 `calc_forward_returns`（任意ホライズン対応）、IC（Spearman）計算 `calc_ic`、ランク化 `rank`、ファクター統計サマリ `factor_summary` を実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。

  - `research/__init__.py`
    - 研究用 API をエクスポート（ファクター計算、正規化ユーティリティの公開）。

- AI / NLP（ニュース）
  - `ai/news_nlp.py`
    - raw_news を使った銘柄別ニュースセンチメント算出モジュールを追加（OpenAI API を利用）。
    - 処理設計:
      - JST ベースのニュースウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST。内部は UTC に変換）。
      - 1 銘柄あたり記事数・文字数でトリムしてバッチ送信（最大 20 銘柄/コール）。
      - 429/ネットワーク/5xx は指数バックオフでリトライ。
      - レスポンスを厳格にバリデートしてスコアを ±1.0 にクリップ、ai_scores テーブルへ書き込み（部分失敗耐性のため対象コードのみ削除→挿入）。
    - OpenAI API キーは引数または環境変数 `OPENAI_API_KEY` から取得。未設定時は ValueError を送出。
    - （注）実装中の箇所がファイル末尾で切れているため、一部処理が未完／継続実装必須。

- ツール
  - `tools/paper_verification_report.py`
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、リスク却下数、API レイテンシ（avg/max/P95）。
    - 基準値（PASS/FAIL）を定義: 稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200ms。
    - CLI オプションで期間フィルタ（--from/--to）および DB パス（--db）を指定可能。
    - DB 存在チェックや SQL 実行の OperationalError 耐性を有する（テーブル欠落時は N/A または 0 で扱う）。

### 変更
- 設定自動ロードの優先順位を明確化: OS 環境変数 > .env.local > .env。
- `run_monitoring` と `run_execution` の起動フローにおいて、プロセス優先度設定を起動直後に行うよう統一。
- `run_monitoring` は Monitoring 用 DB に常に production の sqlite_path を使用する仕様（環境に依存しない）。

### 修正（堅牢化・バグ回避）
- `.env` パーサーの改善により、クォート内のバックスラッシュエスケープや export プレフィックス、行末コメントの誤解釈を回避。
- `calc_score_weights` が全スコア 0 の場合に等分配へフォールバックするように警告を追加。
- 各種ファクター計算・統計関数でデータ不足時に None を返すなど NULL/欠損への耐性を強化。
- `position_sizing` の合計投下スケールダウン処理で小数端数の再配分アルゴリズムを実装（lot 単位で安定的に再配分）。
- `utils.process_priority` は権限不足や未対応プラットフォームで安全にスキップするように修正（警告ログを出力）。

### 既知の問題 / 注意点
- `ai/news_nlp.py` はファイル末尾が切れているため（現状のソースは途中で終端）、完全な動作確認・補完が必要。特に記事フェッチ部分や DB 書き込みの最終処理は継続実装が必要。
- `position_sizing` における価格欠損時のフォールバック（前日終値や取得原価の使用）は未実装（TODO）。価格が 0.0 の場合にエクスポージャーが過少見積りされる可能性あり。
- DuckDB に対する複数行 insert/executemany 周りの注意点（空 params 回避など）は実装メモとして残っているため、バージョン差分での動作確認が必要。
- 一部の設定値（閾値や RiskConfig のデフォルト）はコード内にハードコードされているため、運用時に環境変数等でのチューニングを検討してください。

## Deprecated
- なし

## Removed
- なし

## Security
- なし

---

（開発メモ）
- 次版では AI モジュールの未完実装部分の補完、単体テストの追加、ドキュメントの拡充（API 使用例や運用手順）を優先予定です。