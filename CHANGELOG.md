# Changelog

すべての注目すべき変更を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  
バージョン番号はセマンティックバージョニングに従います。

なお、この CHANGELOG はリポジトリ内のソースコード（src/kabusys 以下）から機能や設計方針を推測して作成しています。

## Unreleased

- なし

## [0.1.0] - 2026-03-29

初回リリース。日本株自動売買システムの基礎機能群を実装・公開。

### Added

- パッケージ基盤
  - kabusys パッケージを公開（__version__ = "0.1.0"）。
  - 公開 API: data, strategy, execution, monitoring を __all__ で提供。

- 設定管理（kabusys.config）
  - .env ファイルと OS 環境変数から設定値を読み込む自動ローダーを実装。
    - プロジェクトルート検出は __file__ を基点に `.git` または `pyproject.toml` を探索。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env（既存の OS 環境変数は保護）。
    - 自動ロードを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート（テスト用途）。
  - .env パース機能を実装（コメント、export プレフィックス、クォートとエスケープ対応、インラインコメントの扱い等）。
  - Settings クラスを提供し、アプリケーション設定をプロパティ経由で取得可能。
    - J-Quants / kabuステーション / Slack / DB パス（DuckDB/SQLite）等の設定プロパティ。
    - KABUSYS_ENV（development/paper_trading/live）や LOG_LEVEL のバリデーション。
    - 必須環境変数未設定時は ValueError を送出する `_require` を採用。

- データ層（kabusys.data）
  - カレンダー管理（calendar_management）
    - JPX カレンダー（market_calendar）を扱うユーティリティを実装。
    - 営業日判定 API: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB 登録値優先、未登録日は曜日ベースのフォールバック。探索範囲上限を設定して無限ループを回避。
    - 夜間バッチ更新 job: calendar_update_job により J-Quants から差分取得・冗長取得（バックフィル）・保存を実行。
    - 健全性チェック（未来日付の異常検知など）とログ出力。

  - ETL パイプライン（pipeline / etl）
    - ETLResult データクラスを公開（ETL の取得数・保存数・品質問題・エラー等の集約）。
    - ETL 処理方針: 差分更新、バックフィル、品質チェックの実装方針を準備（jquants_client / quality との連携）。
    - エラー／品質問題は集約して呼び出し元に伝える設計（Fail-Fast ではなく全件収集）。
    - etl モジュールから ETLResult を再エクスポート。

  - jquants_client と連携する前提での DB ヘルパー実装（テーブル存在確認、最大日付取得など）。

- AI モジュール（kabusys.ai）
  - ニュース NLP（news_nlp）
    - target_date に基づくニュース取得ウィンドウ計算（JST 基準から UTC naive datetime に変換）を提供（calc_news_window）。
    - raw_news と news_symbols を結合して銘柄ごとに記事を集約（_fetch_articles）。
    - OpenAI（gpt-4o-mini）を用いたバッチセンチメント評価（score_news）。
      - 1回の API 呼び出しで最大 20 銘柄を処理するチャンク方式を採用（_BATCH_SIZE）。
      - 1銘柄あたりの記事数と文字数の上限設定（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
      - JSON Mode を利用しレスポンスを厳密に検証。部分失敗時の保護のため書き込みは対象コードの削除→挿入方式。
      - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ。
      - API 呼び出し箇所はテスト可能に設計（_call_openai_api を patch 可能）。
      - スコアは ±1.0 にクリップ。フォールトトレラントな設計（失敗時は該当チャンクをスキップし継続）。
  - 市場レジーム判定（regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次レジーム（bull/neutral/bear）を判定（score_regime）。
    - ma200_ratio の計算、マクロキーワードでフィルタした raw_news の抽出、OpenAI を用いたマクロセンチメント評価を実装。
    - API のリトライ・エラー処理、レスポンス JSON パースのフェイルセーフ（失敗時 macro_sentiment=0.0）。
    - 計算結果は market_regime テーブルへ冪等（BEGIN / DELETE / INSERT / COMMIT）で書き込み。
    - OpenAI API キーは引数または環境変数 OPENAI_API_KEY から取得、未設定時は ValueError。

- リサーチ（kabusys.research）
  - factor_research
    - Momentum, Volatility, Value 等のファクター計算を提供。
      - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（データ不足時に None を返す）。
      - calc_volatility: 20日 ATR（atr_20）・相対 ATR（atr_pct）・平均売買代金・出来高比率等。
      - calc_value: raw_financials から最新財務データを取得し PER / ROE を計算（EPS が 0/欠損時は None）。
    - DuckDB 上の SQL と Python を組み合わせて効率的に実行。外部 API 呼び出しは行わない設計。
  - feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: スピアマン順位相関（Information Coefficient）を実装（rank 関数で同順位は平均ランク）。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を計算。
    - 簡潔で外部依存のない実装を志向（pandas 等に依存しない）。

- 実装上の設計方針・品質配慮（ドキュメント化された点）
  - ルックアヘッドバイアス防止: 各スコアリング/計算関数は datetime.today() / date.today() を内部参照せず、必ず target_date を引数に取る。
  - DB 書き込みは冪等に行う（DELETE→INSERT、ON CONFLICT による上書き等）。
  - API 呼び出しはリトライおよびフェイルセーフによりシステム全体の堅牢性を確保（部分失敗を許容）。
  - DuckDB を一次 DB として利用する前提の SQL 実装。
  - テスト容易性のため、OpenAI 呼び出し箇所に差し替えポイントを用意（unittest.mock.patch 等でモック可能）。
  - ロギングと詳細な警告メッセージを多用し、障害解析を容易にする。

### Security

- OpenAI API キーは外部に露出しないよう設計（環境変数または明示的引数で渡す）。必須未設定時は ValueError を送出して明示的に失敗させる箇所あり。

### Notes / Known limitations

- news_nlp / regime_detector ともに OpenAI の JSON Mode を想定したレスポンス処理を行うが、実運用ではモデルや API 仕様の変化によりパースコードや retry ポリシーの調整が必要になる可能性がある。
- DuckDB バインド・executemany の挙動（空リストを許容しない等）に対するワークアラウンドを実装しているため、DuckDB バージョン依存性に注意。
- 現バージョンでは PBR や配当利回りなど一部バリューファクターは未実装。
- J-Quants / kabu ステーション等の外部クライアント実装（jquants_client 等）は別モジュールとして想定され、ここでは利用点のみを定義。

---

以上がこのコードベースから推測される 0.1.0 のリリース内容です。  
追加の情報（実際のコミット履歴やリリースノート）があれば、より正確で細かい CHANGELOG の作成が可能です。必要なら出力形式の調整（英語版、リリースノート分割、セクション追加等）も対応します。