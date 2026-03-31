# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
このファイルはコードベースから推測して作成しています。実際のリリース履歴と差異がある場合があります。

なお初期バージョンとして 0.1.0 を公開しています（リリース日: 2026-03-31）。

## [Unreleased]
- （現在のコードベースに基づく初期リリースのみ作成済み）

## [0.1.0] - 2026-03-31

### Added
- パッケージの初期実装を追加。
  - パッケージ名: kabusys、バージョン: 0.1.0
  - パブリックモジュール: data, research, ai, config, などを含むパッケージ構成を公開。
- 環境変数/設定管理
  - 自動 .env ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml）。
  - .env と .env.local の読み込み順序を実装（.env.local が上書き）。
  - export プレフィックスやシングル/ダブルクォート、エスケープ、インラインコメント等に対応した .env パーサを実装。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを実装し、J-Quants / kabuステーション / Slack / DB パス / ログレベル等の設定アクセスを提供。
  - 必須設定が未定義の場合に ValueError を送出する _require を実装。
  - KABUSYS_ENV と LOG_LEVEL の値検証を実装（許容値の定義）。
- データプラットフォーム（data モジュール）
  - ETL 基盤: pipeline.ETLResult を公開（ETL 実行結果の集約と状態判定）。
  - calendar_management: JPX カレンダー管理（market_calendar の読み書き、営業日判定、next/prev_trading_day、get_trading_days、SQ 判定、夜間バッチ更新 job）を実装。
    - DB にデータがない場合は曜日ベース（週末除外）のフォールバックを行う設計。
    - カレンダー先読み / バックフィル / 健全性チェックを実装。
  - ETL モジュール（pipeline）: 差分取得、保存、品質チェック連携用のユーティリティを実装。backfill の考慮と品質問題の収集方針を明示。
- 研究 (research)
  - factor_research: モメンタム（1M/3M/6M, MA200乖離）、ボラティリティ（20日ATR 等）、バリュー（PER, ROE）等のファクター計算を DuckDB SQL と Python で実装。
  - feature_exploration: 将来リターン計算（任意ホライズン）、IC（Spearman の ρ）計算、ランク付けユーティリティ、ファクター統計サマリーを実装。外部ライブラリ非依存で実装。
  - 研究用ユーティリティ zscore_normalize を data.stats から利用可能にするエクスポートを準備。
- AI 系機能 (ai)
  - news_nlp: ニュース記事を銘柄ごとに集約して OpenAI（gpt-4o-mini）に送信し、銘柄ごとのセンチメントを ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ（前日15:00 JST ～ 当日08:30 JST）を計算する calc_news_window を実装。
    - バッチ処理（最大 20 銘柄/コール）、記事数・文字数上限トリム、JSON モードを期待したレスポンス検証と ±1.0 のクリッピングを実装。
    - レート制限・ネットワーク断・タイムアウト・5xx の場合は指数バックオフでリトライし、致命的ではない場合はスキップして継続するフェイルセーフ設計。
    - DuckDB executemany の空リスト問題を回避するためのガード実装。
  - regime_detector: ETF（1321）の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して market_regime テーブルへ日次書き込みするロジックを実装。
    - マクロキーワードによる raw_news 抽出、OpenAI 呼び出し、スコア合成、閾値判定（bull/neutral/bear）を実装。
    - API 失敗時のフォールバック（macro_sentiment=0.0）を実装。
  - OpenAI 呼び出しは各モジュール内で独立して実装し、モジュール間でプライベート関数を共有しない方針を採用（結合度低減）。
- ロギングとフェイルセーフ
  - 各重要処理での情報ログ・警告ログ・例外処理（ROLLBACK の失敗ログ含む）を実装。
  - 外部 API の失敗時にサービス全体が停止しないよう、0相当の中立スコアやスキップで継続する動作が多数実装されている。

### Changed
- 初期リリースのため該当なし（新規実装のみ）。

### Fixed
- 初期リリースのため該当なし。

### Security
- 初期リリースのため該当なし。

### Known issues / Limitations
- OpenAI API に依存する機能（news_nlp, regime_detector）は API キーとネットワークが必要。API 呼び出し失敗時は処理を安全に継続する設計だが、結果の欠落が発生する。
- DuckDB バージョン依存の挙動（リスト型バインドの互換性）に対応するためのワークアラウンドを組み込んでいる。環境により調整が必要な場合あり。
- カレンダー / ニュース時間ウィンドウは UTC naive datetime を使用。タイムゾーン混入には注意。
- JSON Mode を想定したレスポンス処理だが、LLM の出力が必ずしも厳密な JSON とは限らないため、パース復元ロジックを実装している。一部ケースでは期待通りに復元できない可能性がある。
- score_news と score_regime は内部で date.today() を参照しないよう設計（ルックアヘッドバイアス防止）。呼び出し時に明示的に target_date を与える必要がある点に注意。
- 現時点で PBR・配当利回り等の一部バリューファクターは未実装。

### Public API（主な公開関数・クラス）
- kabusys.config.settings: Settings インスタンス（設定アクセス）
- kabusys.ai.score_news(conn, target_date, api_key=None) → int
- kabusys.ai.score_regime(conn, target_date, api_key=None) → int
- kabusys.data.ETLResult（pipeline.ETLResult の再エクスポート）
- kabusys.data.calendar_management:
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day, calendar_update_job
- kabusys.research:
  - calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, rank
- その他、DuckDB を前提とした多数の内部ユーティリティ関数群

---

（以降のバージョンはここに追記してください）