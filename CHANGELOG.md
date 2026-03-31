# Changelog

すべての注目すべき変更を記録します。本ファイルは Keep a Changelog の形式に準拠しています。  
システム全体のバージョンはパッケージ定義 (src/kabusys/__init__.py) に合わせて 0.1.0 です。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-31

初回リリース。以下の主要機能・モジュールを実装・公開しました。

### 追加 (Added)
- パッケージ基盤
  - パッケージ情報とエクスポート一覧を定義（kabusys.__init__）。
  - バージョン: 0.1.0。

- 設定管理 (kabusys.config)
  - Settings クラスを実装し、環境変数経由でアプリケーション設定を取得可能に。
  - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能。
  - .env パーサーの強化:
    - export KEY=val 形式対応
    - シングル/ダブルクォート、バックスラッシュエスケープ対応
    - 行末コメントの処理（スペース直前の '#' をコメントとして扱う）
  - 必須環境変数チェック用の _require ユーティリティ。
  - 許容値検証（KABUSYS_ENV, LOG_LEVEL）、デフォルト値（KABUSYS_API_BASE_URL, DB パス等）。

- データ / ETL (kabusys.data)
  - ETLResult データクラスを公開（kabusys.data.pipeline と re-export）。
  - ETL パイプライン基盤（data.pipeline）:
    - 差分取得、バックフィル、保存、品質チェックを想定した設計。
    - DuckDB を使用した最大日付取得、テーブル存在確認ユーティリティ等を実装。
    - エラー/品質情報を収集して ETLResult に保持する仕組み。
  - カレンダー管理 (data.calendar_management):
    - market_calendar を用いた営業日判定ロジックを実装（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 優先の判定と、DB 未取得時の曜日ベースフォールバックを採用。
    - calendar_update_job を実装し、J-Quants クライアントから差分取得して冪等保存（バックフィル・健全性チェック含む）。

- 研究用モジュール (kabusys.research)
  - ファクター計算 (research.factor_research):
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離の算出。
    - calc_volatility: 20日 ATR、相対 ATR、平均売買代金、出来高比率の算出。
    - calc_value: PER、ROE の算出（raw_financials の最新財務データを使用）。
    - DuckDB 上の SQL とウィンドウ関数を組み合わせた実装。
  - 特徴量探索 (research.feature_exploration):
    - calc_forward_returns: 指定ホライズンの将来リターン計算（デフォルト [1,5,21]）。
    - calc_ic: スピアマンランク相関 (Information Coefficient) の算出。
    - rank: 同順位を平均ランクで処理するランク化ユーティリティ。
    - factor_summary: ファクターごとの基本統計量（count/mean/std/min/max/median）。
  - 研究向けユーティリティ群を __all__ で公開。

- AI / NLP (kabusys.ai)
  - ニュースセンチメント (ai.news_nlp):
    - raw_news と news_symbols を用いて銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode でバッチ評価。
    - バッチサイズ、記事数上限、文字数トリム、JST→UTC ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST 相当）の計算を実装。
    - リトライ（429 / ネットワーク / タイムアウト / 5xx）に対する指数バックオフ、失敗時はスキップ（例外は上位へ投げない設計）。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results リスト検証、code の正規化、スコア数値検証、±1.0 クリップ）。
    - DuckDB への冪等書き込み（DELETE → INSERT）で既存スコアを保護する実装。
  - 市場レジーム判定 (ai.regime_detector):
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出。
    - OpenAI 呼び出しのリトライとフォールバック（API 失敗時は macro_sentiment=0.0）。
    - DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）とロールバック処理を実装。
    - LLM 呼び出しは内部で OpenAI クライアントを生成し、テスト容易性のため呼び出し関数を差し替え可能に設計。

### 変更・設計上の要点 (Changed / Notes)
- ルックアヘッドバイアス対策
  - 日時の算出で datetime.today()/date.today() に依存する処理を避け、外部から target_date を与える設計に統一。
  - prices_daily 等のクエリは target_date 未満／未満区間を明示してルックアヘッドを防止。

- 耐障害性・冪等性
  - DB 書き込みは冪等化（DELETE→INSERT/ON CONFLICT 的手法）し、失敗時にロールバックを行う。
  - OpenAI API 呼び出し失敗時は例外を投げずフォールバックする箇所（news_nlp/regime_detector）が存在し、システム全体が停止しない設計。

- DuckDB 互換性考慮
  - executemany に空リストを渡さない等、DuckDB の挙動差分を考慮した実装。
  - 日付変換ユーティリティ (_to_date) を用いて DuckDB からの戻り値を安全に date 型へ変換。

- テスト容易性
  - OpenAI 呼び出しラッパー関数（_call_openai_api）を明示的に分離し、unittest.mock.patch による差し替えを想定。
  - API キー注入パラメータ(api_key)を多くの関数で受け取り、環境依存を排除。

### 修正 (Fixed)
- .env パーサーの改善により以下を修正:
  - クォート内のバックスラッシュエスケープ処理漏れを修正。
  - export プレフィックスや行末コメントの誤解釈を改善。
- LLM レスポンス処理の堅牢化:
  - JSON mode でも前後に余計なテキストが混ざるケースへ対応（最外の {} を抽出してパース）。
  - LLM が数値コードを返すケースに対してコード値を str に正規化して照合することでスコア取得漏れを低減。

### セキュリティ (Security)
- 本リリースでは特段のセキュリティ修正はありません。環境変数に API キー等の機密を置く設計のため、運用時は OS の環境変数やシークレット管理を推奨します。

---

記載はコードの実装内容から推測して作成しています。実際のリリースノートとして用いる場合は、コミット履歴やリポジトリの CHANGELOG ポリシーに合わせて調整してください。