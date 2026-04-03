# Changelog

すべての重要な変更は Keep a Changelog のフォーマットに従って記載します。  
このプロジェクトはセマンティックバージョニングに従います。

## [0.1.0] - 2026-04-03

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。パッケージの公開インターフェースとして data/strategy/execution/monitoring を __all__ に設定。
- 環境設定 (kabusys.config)
  - .env ファイルおよび環境変数からの設定読み込みを実装。
  - 自動ロード処理:
    - プロジェクトルート検出（.git または pyproject.toml を探索）に基づき .env / .env.local を自動読み込み。
    - .env.local は .env を上書きする優先度で読み込まれる。OS 環境変数は保護（上書き禁止）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env パーサーの強化:
    - export KEY=val 形式のサポート、クォート内バックスラッシュエスケープ処理、インラインコメントの扱いを実装。
  - Settings クラスを提供（settings インスタンス経由でアクセス可能）。J-Quants / kabu API / LINE / DB パス / 監視閾値 / システム環境（development/paper_trading/live）などの設定プロパティを用意。
  - 必須環境変数取得時に未設定なら ValueError を送出するユーティリティ _require を実装。
- AI モジュール (kabusys.ai)
  - ニュースセンチメント (news_nlp.score_news)
    - raw_news, news_symbols を集約して OpenAI（gpt-4o-mini）にバッチ送信し、銘柄ごとの ai_score（-1.0〜1.0）を ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ: 前日 15:00 JST 〜 当日 08:30 JST（UTC に変換して DB 比較）。
    - バッチ処理（最大 20 銘柄/回）、1銘柄あたり最大 10 記事・最大 3000 文字にトリム。
    - JSON Mode のレスポンスを堅牢にパース・バリデーション（余分な前後テキストの復元処理含む）。
    - 429/network/timeout/5xx に対して指数バックオフでリトライ、失敗時はフォールバック（スキップ）して処理継続。
    - API キーは引数または環境変数 OPENAI_API_KEY で指定。未指定時は ValueError。
  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次でレジーム判定（bull/neutral/bear）を行い、market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出はキーワードベース（日本/米国等のマクロ用キーワードリスト）。
    - LLM 呼び出しは gpt-4o-mini、API エラーに対するリトライ/フェイルセーフ（失敗時 macro_sentiment=0.0）。
    - API キーは引数または環境変数 OPENAI_API_KEY で指定。未指定時は ValueError。
- リサーチ (kabusys.research)
  - factor_research モジュール:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離等を計算。データ不足時は None を返す。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算。
    - calc_volatility: 20 日 ATR / 相対 ATR / 平均売買代金 / 出来高比率を計算。
    - DuckDB ベースの SQL + Python 実装で、prices_daily / raw_financials のみ参照。
  - feature_exploration モジュール:
    - calc_forward_returns: 将来リターン（任意ホライズン）を一括取得する効率的クエリを実装。
    - calc_ic: スピアマンランク相関（IC）を実装（有効レコード 3 件未満なら None）。
    - rank / factor_summary: ランク変換・基本統計量サマリーを実装。
  - research パッケージ __all__ で主要関数を再エクスポート。
- データプラットフォーム (kabusys.data)
  - calendar_management:
    - JPX カレンダー（market_calendar）を基に営業日判定 / next/prev_trading_day / get_trading_days / is_sq_day を提供。
    - DB 登録値を優先し、未登録日は曜日ベース（週末除外）でフォールバック。最大探索範囲を設けて無限ループを防止。
    - calendar_update_job: J-Quants クライアント経由で差分取得し、冪等保存（バックフィル・健全性チェック実装）。
  - ETL / pipeline:
    - ETLResult データクラスを公開（kabusys.data.etl 経由で re-export）。
    - pipeline モジュールに ETL 実行結果管理・テーブル存在チェック・最大日付取得等の基盤実装（差分取得 / 品質チェックを想定した設計）。
  - jquants_client との連携を想定した差分取得 / 保存 / 品質チェックの設計方針を明記（実装は jquants_client モジュールに委譲）。
- エラーハンドリング・ロギング
  - 各モジュールで情報/警告/例外ログを適切に記録するように実装。
  - DB 書き込み時は BEGIN/DELETE/INSERT/COMMIT の冪等パターンを採用し、例外時は ROLLBACK をトライしてログ記録。

### 変更 (Changed)
- （初期リリースのため該当なし）

### 修正 (Fixed)
- （初期リリースのため該当なし）

### 非推奨 (Deprecated)
- （初期リリースのため該当なし）

### 削除 (Removed)
- （初期リリースのため該当なし）

### セキュリティ (Security)
- OpenAI API キー等の機密情報は Settings を通して環境変数で管理する設計。自動 .env 読み込みは明示的に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

---

変更点はコードベースから推測して記載しています。必要であれば各機能ごとに利用方法例・注意点（必須環境変数一覧、DB スキーマの前提など）を別途追記します。