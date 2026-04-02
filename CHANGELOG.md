# Changelog

すべての変更は Keep a Changelog のフォーマットに準拠しています。  
リリースはセマンティックバージョニングに従います。

## [0.1.0] - 2026-04-02

### 追加 (Added)
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ を定義。
- 環境設定・自動 .env ローダー (src/kabusys/config.py)
  - プロジェクトルート検出（.git または pyproject.toml を基準）により、CWD に依存しない .env 自動読み込みを実装。
  - .env/.env.local の優先順位と OS 環境変数の保護（protected set）をサポート。
  - 行パーサは export 形式、クォート、エスケープ、インラインコメントの扱いに対応。
  - 環境変数アクセス用 Settings クラスを提供（J-Quants, kabu API, Slack, DB パス, 監視閾値, 環境・ログレベル検証など）。
  - 自動読み込みの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
- AI モジュール群 (src/kabusys/ai)
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini, JSON mode）でセンチメントを評価。
    - バッチ処理（最大 20 銘柄/コール）、トークン肥大対策（記事数・文字数トリム）、最大リトライ・指数バックオフ、レスポンス検証、スコアの ±1.0 クリップを実装。
    - calc_news_window: JST ベースのニュース収集ウィンドウ計算ユーティリティを提供（ルックアヘッドバイアス対策のため日付取得は caller に委譲）。
    - ai_scores テーブルへの冪等書き込み（DELETE → INSERT: 部分失敗時に既存データを保護）。
    - テスト用フック: _call_openai_api の差し替えが容易（unittest.mock.patch を想定）。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジームを判定（bull / neutral / bear）。
    - prices_daily, raw_news を参照し、market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - API エラー時は macro_sentiment=0.0 で継続するフェイルセーフ設計。
    - OpenAI 呼び出しはモジュール内の専用関数で行い、他モジュールとの結合を避ける。
- データプラットフォーム関連 (src/kabusys/data)
  - マーケットカレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar テーブルを用いた営業日判定ユーティリティ群: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB データ優先。ただし未登録日は曜日（平日/土日）ベースでフォールバック。最大探索日数の上限を設定して無限ループを回避。
    - calendar_update_job: J-Quants API から差分取得し market_calendar を冪等更新（バックフィル、健全性チェックあり）。
  - ETL パイプライン基盤 (src/kabusys/data/pipeline.py / src/kabusys/data/etl.py)
    - ETLResult dataclass を公開（エラー/品質問題の集約、to_dict メソッドを提供）。
    - 差分取得、保存（jquants_client の save_* を利用して idempotent 保存）、品質チェックとの連携方針を文書化。
    - src/kabusys/data/etl.py で ETLResult を再エクスポート。
- Research モジュール (src/kabusys/research)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - calc_momentum: 1M/3M/6M リターン、ma200 乖離を計算（データ不足時は None）。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算（データ不足で None）。
    - calc_value: raw_financials の最新財務データと当日株価から PER、ROE を計算。
    - DuckDB を用いた SQL + Python 実装で外部 API への影響なし。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - calc_forward_returns: 指定ホライズンの将来リターンを一括取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。
    - rank / factor_summary: ランク変換とカラムの統計サマリーを提供。
  - src/kabusys/research/__init__.py で主要関数と zscore_normalize をエクスポート。

### 変更 (Changed)
- 設計方針の明確化
  - 全ての分析系処理（ニューススコア、レジーム判定、ファクター計算等）で datetime.today() / date.today() 参照を避け、caller が target_date を渡すことでルックアヘッドバイアスを防止する設計を徹底。
  - DuckDB をメインのローカル分析用 DB として使用。DB 書き込みは可能な限り冪等に実装。
  - OpenAI 呼び出しに対してリトライ戦略（429/ネットワーク/タイムアウト/5xx）を導入し、非致命的失敗時は処理を継続するフェイルセーフを採用。

### 修正 (Fixed)
- （初回公開のため明示的な「修正」はなし。実装時に想定されたフォールトトレランスやロジック検証を組み込み済み。）

### 注意事項 / 既知の問題 (Known issues)
- src/kabusys/data/pipeline.py の末尾に実装途上と思われる箇所が存在します（ファイル末尾に "return date.fro" で途切れている）。このままでは構文エラーとなり、該当関数の完全な動作（特に _get_max_date の末尾処理）が阻害される可能性があります。リリース前に該当箇所の修正・確認を推奨します。
- J-Quants / OpenAI など外部 API を使用する機能は、適切な API キー設定およびネットワークアクセス環境が必要です。環境変数が未設定の場合は ValueError を送出する箇所があるため、CI / 実行環境での環境設定に注意してください。
- DuckDB バインディング（executemany の空リスト等）に関してバージョン依存の注意点がコード内に記載されています。運用環境の DuckDB バージョンによっては追加の互換対応が必要となる可能性があります。

### 互換性の破壊 (Breaking Changes)
- 初期リリースのため、破壊的変更はありません。ただし上記の既知の問題を含め、今後のマイナー/パッチで修正が入る可能性があります。

### セキュリティ (Security)
- 本リリースにおける既知のセキュリティ問題は報告されていません。ただし API キーやパスワード等の機密情報は環境変数 / .env により管理する設計のため、取り扱いには注意してください（.env をリポジトリに含めない等）。

---

今後の予定（例）:
- pipeline._get_max_date を含む未完了箇所の修正。
- 単体テスト・統合テストの追加（外部 API をモック化した CI 実装）。
- ドキュメント（Usage / Deployment / Data Schema）の拡充。