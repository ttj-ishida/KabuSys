# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このファイルはコードベースから推測して作成した初回リリースの変更履歴です。

なお、日付は本リリース作成日です。

## [Unreleased]

## [0.1.0] - 2026-03-28

初回公開リリース。日本株自動売買・データ基盤・リサーチ用ユーティリティ群を提供します。
主な特徴は以下の通りです。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージを追加。バージョンは 0.1.0。
  - __all__ に data, strategy, execution, monitoring を公開。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - プロジェクトルート探索は __file__ を起点に .git または pyproject.toml を探索（CWD に依存しない）。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env のパース機能を実装（コメント、export プレフィックス、クォート・エスケープ、インラインコメント処理に対応）。
  - Settings クラスを提供（settings インスタンスを公開）。J-Quants、kabuステーション、Slack、DB パス、実行環境やログレベル等のプロパティを定義。
    - 必須変数未設定時には ValueError を送出する _require を使用。
    - KABUSYS_ENV（development / paper_trading / live）や LOG_LEVEL の値検証を実装。

- AI 関連 (kabusys.ai)
  - news_nlp モジュール
    - raw_news と news_symbols から銘柄別ニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルへ書き込む機能を実装（score_news）。
    - 処理の詳細:
      - 独自のニュース時間ウィンドウ計算 (前日 15:00 JST ～ 当日 08:30 JST を UTC に変換) を行う calc_news_window を公開。
      - 1 銘柄あたりの最大記事数・最大文字数制限、バッチ送信（最大 20 銘柄）などトークン対策を組み込み。
      - JSON Mode を利用した厳密な JSON 応答検証、レスポンスのバリデーションとスコアの ±1.0 クリッピングを実装。
      - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。失敗時は個別チャンクをスキップして処理を継続（フェイルセーフ）。
      - DuckDB への書き込みは冪等性を考慮（DELETE → INSERT、executemany を使用、空リストの扱いに注意）。
      - テスト容易性のため _call_openai_api を patch で差し替え可能に設計。
  - regime_detector モジュール
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定し、market_regime テーブルへ冪等書き込みする score_regime を実装。
    - マクロニュース抽出用のキーワード集合と LLM(JSON Mode) を用いたセンチメント評価の仕組みを実装。
    - OpenAI API 呼び出しは独自実装でモジュール結合を避け、API 失敗時は macro_sentiment=0.0 とするフェイルセーフを採用。
    - 各種定数（重み、閾値、モデル名、リトライ等）を定義。

- データプラットフォーム関連 (kabusys.data)
  - calendar_management モジュール
    - JPX カレンダー管理機能を実装（market_calendar テーブルの参照・更新・営業日判定）。
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day 等のユーティリティを提供。
    - DB にカレンダーがない場合は曜日ベースでフォールバックする挙動を実装。探索の最大日数上限で無限ループを防止。
    - calendar_update_job を実装し、J-Quants API から差分取得 → 保存（バックフィル / 健全性チェック付き）する夜間ジョブの骨格を提供（jquants_client を利用）。
  - ETL / パイプライン (kabusys.data.pipeline, kabusys.data.etl)
    - ETLResult データクラスを追加（ETL 実行結果・品質問題・エラーメッセージ等を集約）。
    - 差分取得、保存（idempotent）、品質チェック連携の設計方針をコードに反映。
    - jquants_client / quality モジュールと連携する想定。
    - etl モジュールは pipeline.ETLResult を再エクスポート。

- リサーチ関連 (kabusys.research)
  - factor_research モジュール
    - calc_momentum, calc_volatility, calc_value を実装。prices_daily / raw_financials のみを参照して各種ファクター（モメンタム、MA200 乖離、ATR、流動性、PER/ROE 等）を計算。
    - データ不足時の None 取り扱いやスキャン範囲バッファ等の実装。
  - feature_exploration モジュール
    - calc_forward_returns: 任意ホライズン（デフォルト 1,5,21 営業日）の将来リターン計算を実装。引数検証あり。
    - calc_ic: スピアマンのランク相関（IC）計算を実装。
    - rank: 同順位は平均ランクで扱うランク変換ユーティリティを実装（丸めで ties の安定化）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー機能を実装。
  - research.__init__ で主要関数を公開し、data.stats.zscore_normalize を再利用可能に公開。

### 変更 (Changed)
- 初回リリースのため履歴上の「変更」はありませんが、設計上以下の方針を採用:
  - ルックアヘッドバイアス防止: datetime.today() / date.today() を内部ロジックで直接参照せず、target_date を明示的に受け取る設計（news_nlp, regime_detector, research 等）。
  - モジュール間の結合度を低く保つため、OpenAI 呼び出しの内部関数はモジュール間で共有しない実装。
  - DuckDB のバージョン固有の制約（executemany の空リスト不可、リスト型バインドの挙動等）に配慮して実装。

### 修正 (Fixed)
- 初回リリースのため既存バグ修正はなし（ベース実装を提供）。

### 既知の制限・注意点 (Notes / Known limitations)
- OpenAI API を利用する機能は API キー（OPENAI_API_KEY）を必要とする。api_key 引数で注入可能。
- .env 自動ロードはプロジェクトルート検出に依存するため、配布後の環境やテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD により制御可能。
- DuckDB 依存の SQL 実装はバージョン差異により動作差があり得る（特に executemany / リストバインド関連）。テスト環境での検証を推奨。
- AI モジュールは LLM の応答形式に厳密に依存するため、モデル挙動の変化によりパース・バリデーション処理の調整が必要になる場合がある。

### セキュリティ (Security)
- 本リリースにおけるセキュリティ修正項目はなし。API キー等の機密情報は環境変数で管理する設計を採用。

---

このCHANGELOGはコードから推測して作成しています。将来の変更では、Added / Changed / Fixed / Deprecated / Removed / Security セクションを適宜更新してください。