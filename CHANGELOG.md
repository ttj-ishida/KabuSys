# Changelog

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣習に準拠しています。  

最新版: 0.1.0 — 2026-03-26

## [0.1.0] - 2026-03-26

### 追加 (Added)
- 初期リリースとして以下の主要機能を追加。
  - パッケージ構成
    - kabusys パッケージの公開インターフェースを定義（__version__ = 0.1.0、__all__ に data/strategy/execution/monitoring を含む）。
  - 設定管理 (`kabusys.config`)
    - .env / .env.local を自動読み込みするロジックを実装（プロジェクトルート検出は .git または pyproject.toml 基準）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
    - .env パーサーは export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント等に対応。
    - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス等の必須/既定設定をプロパティとして取得可能。未設定時の検証（_require）を実装。
    - KABUSYS_ENV（development/paper_trading/live）や LOG_LEVEL のバリデーションを実装。
  - AI（自然言語処理）モジュール (`kabusys.ai`)
    - ニュースセンチメント解析: score_news(conn, target_date, api_key=None)
      - raw_news と news_symbols を集約して銘柄毎のニューステキストを作成し、OpenAI（gpt-4o-mini、JSON Mode）へバッチ（最大 20 銘柄/チャンク）で送信。
      - チャンク単位のリトライ（429・ネットワーク断・タイムアウト・5xx を対象）・指数バックオフ実装。
      - レスポンスの厳密なバリデーションとスコアの ±1 クリッピング。
      - DuckDB の ai_scores テーブルへ冪等的に（DELETE → INSERT）書き込み。
      - テスト向けに _call_openai_api を差し替え可能。
    - 市場レジーム判定: score_regime(conn, target_date, api_key=None)
      - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で 'bull'/'neutral'/'bear' を判定。
      - raw_news からマクロキーワードでフィルタして記事を収集、OpenAI 呼び出しは個別の内部実装で結合を防止。
      - API 失敗時は macro_sentiment=0.0 にフォールバックし処理継続。
      - market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
  - データプラットフォーム・ユーティリティ (`kabusys.data`)
    - カレンダー管理モジュール（calendar_management）
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。market_calendar テーブルがない場合は曜日ベースでフォールバック。
      - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新。バックフィルと健全性チェック実装。
    - ETL パイプライン（pipeline）
      - ETLResult データクラスを公開（取得数・保存数・品質問題・エラー集約、to_dict、状態判定プロパティ等）。
      - 差分更新、バックフィル方針、品質チェックを想定した設計（jquants_client / quality と連携する想定）。
    - ETL の公開インターフェースを etl モジュールで再エクスポート（ETLResult）。
  - リサーチモジュール (`kabusys.research`)
    - ファクター計算（factor_research）
      - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離などを DuckDB SQL で計算。
      - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比などを計算。
      - calc_value: raw_financials を用いて PER / ROE を計算（対象日は latest 財務データ を使用）。
      - 全関数は DuckDB の prices_daily / raw_financials を参照し、外部 API 呼び出しを行わない設計。
    - 特徴量探索（feature_exploration）
      - calc_forward_returns: 指定基準日から所定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
      - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。
      - rank: 同順位の平均ランク処理を含むランク化ユーティリティ。
      - factor_summary: 各ファクター列の統計量（count/mean/std/min/max/median）を算出。
    - research.__init__ で主要関数を再エクスポート（zscore_normalize は data.stats から再エクスポート想定）。
  - ログ出力とエラーハンドリング
    - 多くの関数で詳細な logger.info/debug/warning/exception を出力。
    - DB 書き込み中の例外発生時は ROLLBACK を試行し、失敗時は警告ログを出力して例外を再送出。

### 変更 (Changed)
- 初期リリースのため該当なし。

### 修正 (Fixed)
- 初期リリースのため該当なし。

### 既知の制限・設計上の注意 (Notable notes / Known limitations)
- OpenAI のモデルとして gpt-4o-mini の JSON Mode を想定している（JSON パース失敗時には容易な復元処理を入れているが、実運用ではレスポンスフォーマットの安定化が必要）。
- AI モジュールは OpenAI API キーを引数で注入可能（api_key）または環境変数 OPENAI_API_KEY を使用。未設定時は ValueError を送出する。
- news_nlp のチャンクング・トリミングロジックにより、1 銘柄あたり最大 _MAX_ARTICLES_PER_STOCK 記事・文字数で制限される（トークン肥大化対策）。
- DuckDB 側の executemany に空リストを渡せない制約をコード内で回避している（空チェック済み）。
- 一部モジュール（例: jquants_client や quality）の実装はこのコードセットに含まれておらず、外部モジュールとの連携が前提。
- 多くの関数はルックアヘッドバイアス防止のため内部で date.today()/datetime.today() を参照しない設計（ただし calendar_update_job などバッチ用処理では date.today() を使用）。
- timezone: データベース上の raw_news.datetime は UTC 想定で、news のウィンドウ計算は JST→UTC の変換（ナイーブな UTC datetime を返す）を行う。実運用ではタイムゾーン扱いに注意が必要。
- 現時点で strategy / execution / monitoring の具体実装は含まれていない（__all__ に名を挙げているが別途実装を想定）。

### セキュリティ (Security)
- 初期リリースのためセキュリティ修正はなし。環境変数や API キーの取り扱いは Settings 経由で行うことを想定しているが、運用時のシークレット管理（Vault 等）は別途検討を推奨。

---

今後のリリースでは以下を検討してください:
- strategy / execution / monitoring の実装追加（取引実行ロジック、監視・アラート）。
- テストカバレッジ強化（OpenAI 呼び出しのモック化や DB 操作の単体テスト）。
- レスポンス解析の堅牢性向上（LLM の多様な出力に対するフォールバック改善）。
- メトリクス収集（Prometheus 等）と運用監視の統合。