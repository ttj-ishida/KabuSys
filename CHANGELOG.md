# CHANGELOG

すべての変更は Keep a Changelog の慣例に従って記載しています。  
（コードベースの内容から推測して作成しています。実際のコミット履歴とは異なる場合があります）

## [0.1.0] - 2026-04-01
初回リリース。以下の主要機能・モジュールを追加。

### 追加 (Added)
- 基本パッケージ構成
  - パッケージ名: kabusys
  - エクスポート: data, strategy, execution, monitoring（パッケージトップで __all__ を公開）

- 設定管理（kabusys.config）
  - .env / .env.local の自動読み込み機能を実装（OS 環境変数優先、.env.local は上書き）
  - プロジェクトルート自動検出（.git または pyproject.toml を基準）
  - .env のパース機能強化：
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - インラインコメント扱いの取り扱い（クォート有無で挙動を区別）
  - Settings クラスを提供し、環境変数からアプリ設定をプロパティ形式で取得
    - J-Quants / kabu API / Slack / DB パス / 監視閾値 / 環境（development/paper_trading/live）/ログレベル 等を定義
    - 必須環境変数未設定時は ValueError を送出する _require を用意

- AI 関連（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols から銘柄ごとに記事を集約して OpenAI（gpt-4o-mini）でセンチメント評価
    - JST ベースのニュースウィンドウ計算関数 calc_news_window を実装（UTC 変換）
    - チャンク処理（最大 _BATCH_SIZE=20 銘柄 / チャンク）・トークン肥大化対策（記事数・文字数制限）
    - JSON mode による厳密なレスポンス検証とパース後のバリデーション（未知コード無視、数値チェック、クリッピング ±1.0）
    - レート制限・ネットワーク障害・5xx に対する指数バックオフのリトライ戦略
    - idempotent な DB 書き込み（DELETE → INSERT、DuckDB の executemany 空リスト問題に対応）
    - パブリック API: score_news(conn, target_date, api_key=None)

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次レジーム判定
    - マクロニュース検索（キーワード一覧による raw_news フィルタ）
    - OpenAI 呼び出しは専用実装（news_nlp とプライベート関数を共有しない）
    - API エラー時はマクロセンチメントを 0.0 とするフェイルセーフ
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）、失敗時は ROLLBACK
    - パブリック API: score_regime(conn, target_date, api_key=None)

- リサーチ（kabusys.research）
  - factor_research モジュール
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比等を計算
    - calc_value: raw_financials と株価から PER, ROE を計算（EPS が 0 または欠損の処理を含む）
    - DuckDB を用いた SQL ベースの実装（prices_daily / raw_financials を参照）
  - feature_exploration モジュール
    - calc_forward_returns: 指定日から各ホライズン先の将来リターンを計算（horizons のバリデーションあり）
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算
    - rank: 同順は平均ランクで処理するランク変換ユーティリティ
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）
  - 便利関数の再エクスポート（zscore_normalize など）

- データプラットフォーム関連（kabusys.data）
  - calendar_management
    - market_calendar を基にした営業日判定ロジック
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を実装
    - DB にカレンダーがない場合の曜日ベースのフォールバック（週末は非営業日）
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新（バックフィル・健全性チェックを実装）
  - pipeline / ETL
    - ETLResult dataclass を実装（取得件数、保存件数、品質問題リスト、エラーリスト等を保持）
    - ETL の設計方針として差分更新、バックフィル、品質チェック（quality モジュールとの連携）、id_token 注入によるテスト容易性を記載
  - etl モジュールで ETLResult を再エクスポート

### 変更 (Changed)
- 初回リリースのため該当なし

### 修正 (Fixed)
- 初回リリースのため該当なし

### セキュリティ (Security)
- 初版で外部 API キー（OpenAI 等）を使用するため、API キー未設定時は明示的に ValueError を発生させることで、誤動作を低減する設計を採用

### 設計上の注記 / 重要な実装方針
- ルックアヘッドバイアス防止:
  - 各モジュール（news_nlp, regime_detector, research 等）で datetime.today() や date.today() を直接参照しない設計。必ず target_date を引数で受け取り、クエリでも target_date を基準に過去データのみを使用する。
- フェイルセーフ設計:
  - OpenAI API 等が失敗した場合でも、処理を続行または安全なデフォルト（例: macro_sentiment=0.0）にフォールバックする実装。
- DuckDB とのトランザクション設計:
  - 冪等性を保つため DELETE → INSERT のパターンと BEGIN/COMMIT/ROLLBACK を用いた明示的なトランザクションを採用。
  - DuckDB の executemany に空リストを渡せない点を考慮したガードを導入。
- ロギング:
  - 複数の箇所で logger による情報/警告/例外ログを出力（運用時のトラブルシュートを想定）。

### 既知の問題 (Known issues / TODO)
- src/kabusys/data/pipeline.py の末尾にコード断片（`return date.fro` で終わる箇所）が存在し、ここはおそらく不完全（切り出しミス）です。実際のリポジトリでは該当箇所の修正（正しい日付返却ロジックの復元）が必要です。
- 外部依存:
  - OpenAI SDK と J-Quants クライアント（kabusys.data.jquants_client）が必要。実行環境にこれらの設定（API キー / client 実装）がないと一部機能が動作しません。
- 一部モジュール（例: strategy, execution, monitoring）の実装／公開関数がこのスナップショットに含まれていないため、運用フロー全体の動作確認は実装完了後に必要です。

---

この CHANGELOG はコード内容から推測して作成しています。コミット履歴や実際のリリースノートを用いる場合は、差分を適宜反映してください。