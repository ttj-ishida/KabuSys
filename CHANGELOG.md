# Changelog

すべての重要な変更点を記録します。本ファイルは「Keep a Changelog」仕様に準拠しています。  
注: 以下のリリース内容はコードベースの実装内容から推測して作成したものであり、実際の履歴やリリースノートと異なる場合があります。

## [Unreleased]

- （現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-09

初回公開リリース。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージを追加。version = 0.1.0。
  - パッケージ配下の主要モジュールを公開: data, strategy, execution, monitoring（__all__ に含む）。

- 設定管理
  - 環境変数／.env 読み込みユーティリティを実装（kabusys.config）。
    - プロジェクトルートを .git / pyproject.toml から検出し、自動で .env / .env.local を読み込む（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
    - export KEY=val 形式やクォート・エスケープ・インラインコメント処理に対応したパーサーを実装。
    - Settings クラスを提供し、J-Quants / kabuステーション / LINE / データベース / 監視 / システム関連の設定プロパティを公開。
    - PAPER_FILL_MODE や KABUSYS_ENV / LOG_LEVEL 等の値検証（有効値チェック）を実施。
    - Path 型でのデフォルトパス（duckdb, sqlite, paper_sqlite, pid/kill flag など）をサポート。

- AI（自然言語処理）機能
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）
    - target_date に基づくニュースウィンドウ計算（JSTベース → UTC変換）を実装。
    - raw_news と news_symbols を集約して銘柄ごとに記事をまとめ、OpenAI（gpt-4o-mini）の JSON Mode でバッチ評価。
    - バッチ処理（最大20銘柄／回）、記事数・文字数のトリム、レスポンス検証、スコア ±1.0 クリップ、DuckDB への冪等書き込み（DELETE → INSERT）を実装。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ、失敗時は安全にスキップして継続するフェイルセーフを実装。
    - テスト容易性のため OpenAI 呼び出し部分を差し替え可能（_call_openai_api をモックで差し替え可能）。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（Nikkei225 連動）の 200 日移動平均乖離（重み70%）とニュースの LLM センチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - DuckDB からの価格・ニュース取得、OpenAI（gpt-4o-mini）呼び出し、スコア合成、market_regime テーブルへの冪等書き込みを実装。
    - API エラー時は macro_sentiment=0.0 にフォールバックするフェイルセーフ、並びにリトライロジックを実装。
    - ルックアヘッドバイアス回避のため datetime.today()/date.today() を直接参照しない設計（target_date を明示的に渡す方式）。

- データ処理・ETL
  - ETL 結果クラス ETLResult を公開（kabusys.data.pipeline / kabusys.data.etl の再エクスポート）。
    - ETLResult による取得件数、保存件数、品質チェック問題、エラー情報の集約、has_errors / has_quality_errors / to_dict を提供。
  - ETL パイプライン設計の骨子を実装（差分取得、save_* の冪等保存、品質チェックとの連携等を想定）。

- データ（カレンダー）
  - JPXマーケットカレンダー管理モジュール（kabusys.data.calendar_management）を実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定 API。
    - market_calendar がない場合は曜日ベースのフォールバック（週末は非営業日）。
    - calendar_update_job により J-Quants から差分取得 → market_calendar へ冪等保存する夜間ジョブを実装。
    - 最大探索日数やバックフィル、健全性チェック等を組み込み。

- リサーチ / ファクター分析
  - kabusys.research パッケージを追加。以下の関数群を公開:
    - ファクター計算: calc_momentum, calc_value, calc_volatility（kabusys.research.factor_research）
      - Momentum（1M/3M/6M リターン、200日移動平均乖離）、Value（PER/ROE）、Volatility（20日 ATR）等を DuckDB 上の SQL と Python ロジックで計算。
      - データ不足時の None 戻し、結果は (date, code) をキーとした dict リストで返却。
    - 特徴量探索: calc_forward_returns, calc_ic, factor_summary, rank（kabusys.research.feature_exploration）
      - 将来リターン計算（horizons の検証、単一クエリで取得）、Spearman ランク相関（IC）、統計サマリー、ランク付け実装。
      - 外部ライブラリに依存しない純標準ライブラリ実装（pandas など未使用）。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- 初回リリースのため該当なし。
- 注意: OpenAI API キーは環境変数 OPENAI_API_KEY または関数引数で渡す仕様。キー取り扱いには注意。

### 既知の設計上の注意点 / 動作仕様
- ルックアヘッドバイアス防止: AI / リサーチ関連関数は内部で date.today() を参照せず、必ず target_date を渡す設計。
- OpenAI 呼び出しの冗長性とフォールバック: API 呼び出し失敗時は多くの箇所で安全に 0.0（中立）を返すか処理をスキップし、全体の停止を防ぐ。
- DuckDB 互換性: executemany の空リストバインド回避など、DuckDB（0.10 を想定）の互換性考慮がある。
- 自動 .env 読み込み: パッケージがインポートされた際にプロジェクトルートを基に .env / .env.local を自動で読み込む。テスト等で自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すること。
- テスト支援: OpenAI 呼び出し部分は内部関数をモック差し替え可能にしてあり、単体テストで外部 API に依存しないよう設計されている。

### 互換性 / 移行 (Compatibility / Migration)
- 初回リリースのため既存互換性に関する変更点はなし。

---

（参考）公開されている主要なパブリック API（例）
- kabusys.settings (kabusys.config.Settings のインスタンス)
- kabusys.ai.score_news(conn, target_date, api_key=None)
- kabusys.ai.score_regime(conn, target_date, api_key=None)
- kabusys.data.calendar_update_job(conn, lookahead_days=...)
- kabusys.data.ETLResult（kabusys.data.etl で再エクスポート）
- kabusys.research.calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / rank

もし特定ファイルや機能ごとにより詳細な変更履歴（例: 各関数の仕様変更点、バグ修正履歴など）を生成したい場合は、その対象ファイルの差分や追加履歴情報を教えてください。