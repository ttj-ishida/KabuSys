# Changelog

すべての注目すべき変更をここに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-03-28

初回リリース — 基本的なデータ基盤・リサーチ・AI解析・設定管理を提供する日本株自動売買ライブラリを追加。

### 追加 (Added)
- パッケージ基礎
  - kabusys パッケージ初期化（__version__ = 0.1.0）。
  - サブパッケージ公開: data, strategy, execution, monitoring（__all__ 指定）。

- 環境設定管理 (kabusys.config)
  - .env または環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索（CWD 非依存）。
    - 読み込み順: OS環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能。
    - export 形式やクォート付き値、行内コメントなど多様な .env 記法に対応するパーサ実装。
  - Settings クラスを提供（J-Quants / kabuAPI / Slack / DB パス / 環境判定 / ログレベルなどのプロパティ）。
    - 必須環境変数は _require() で明示的なエラーを投げる。
    - KABUSYS_ENV と LOG_LEVEL のバリデーション。

- AI モジュール (kabusys.ai)
  - news_nlp
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）を用いて銘柄ごとのニュースセンチメント（ai_score）を算出。
    - バッチ処理（最大 20 銘柄 / リクエスト）、トークン肥大対策（記事数・文字数制限）、レスポンスバリデーションを実装。
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライを実装。失敗時はフェイルセーフでスキップ。
    - calc_news_window() により JST の業務時間ウィンドウ（前日15:00～当日08:30）を UTC naive datetime で計算。
    - テスト容易性のため _call_openai_api を patch で差し替え可能。
  - regime_detector
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュースマクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - LLM 呼び出しは gpt-4o-mini、JSON Mode で結果を取得。API 失敗時は macro_sentiment=0.0 のフォールバック。
    - DB への書き込みは冪等に BEGIN / DELETE / INSERT / COMMIT を用いて実行。
    - ルックアヘッドバイアス防止のため datetime.today()/date.today() を直接参照しない設計（target_date ベースで処理）。

- Research モジュール (kabusys.research)
  - factor_research
    - モメンタム（1M/3M/6M リターン、200日MA乖離）、ボラティリティ（20日ATR／相対ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER/ROE）を DuckDB の prices_daily / raw_financials を用いて計算する関数群を実装。
    - データ不足ケースは None を返す仕様。
  - feature_exploration
    - 将来リターン calc_forward_returns（任意ホライズン、入力バリデーションあり）。
    - スピアマンランク相関に基づく IC 計算 calc_ic（最小サンプル数チェックあり）。
    - ランク変換ユーティリティ rank（同順位は平均ランク）。
    - 統計サマリー factor_summary（count/mean/std/min/max/median）。
  - research パッケージは一部ユーティリティ（zscore_normalize）を data.stats から再エクスポート。

- Data プラットフォーム (kabusys.data)
  - calendar_management
    - JPX カレンダー（market_calendar テーブル）に基づく営業日判定ユーティリティを実装。
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
      - DB データがない場合は曜日ベース（土日非営業）でフォールバック。
      - 最大探索日数制限で無限ループ防止。
    - calendar_update_job: J-Quants クライアント経由でカレンダーを差分取得し、冪等保存（バックフィル・健全性チェックあり）。
  - pipeline / etl
    - ETLResult データクラスを実装（取得件数、保存件数、品質チェック結果、エラー一覧等を含む）。
    - ETL パイプラインの補助ユーティリティ（最終日取得、テーブル存在チェック、トレーディングデイ調整等）。
    - デフォルトバックフィル、品質チェック連携、id_token 注入によるテスト容易性設計。
  - jquants_client など外部クライアント呼び出しポイントを想定（fetch/save の抽象化）。

- その他設計上の注記
  - DuckDB を主なストレージエンジンとして使用。SQL と Python を組み合わせた計算処理を採用。
  - 多くの箇所で「ルックアヘッドバイアス防止」を明確に設計（target_date 未満/以前のみ参照する等）。
  - DB 書き込みは部分失敗を考慮（コード単位で削除→挿入）して既存データを保護。
  - 詳細ログ出力（info/debug/warning）を各処理で実装。

### 変更 (Changed)
- 初版のため該当なし。

### 修正 (Fixed)
- 初版のため該当なし。

### セキュリティ (Security)
- API キーの取得は引数優先 → 環境変数へフォールバックの安全なフローを実装。OpenAI キー未設定時は ValueError を投げ明示的に通知。
- 自動 .env ロードを無効化する環境変数（KABUSYS_DISABLE_AUTO_ENV_LOAD）を提供し、テストや運用でのキー漏洩リスクを低減。

### 既知の制約・注意点 (Known Issues / Notes)
- OpenAI 依存: news_nlp / regime_detector は OpenAI API（gpt-4o-mini）を前提としており、API 利用制限・コストに注意。
- DuckDB バージョン依存: executemany に空リストを渡せないケース等へのワークアラウンドを実装しているが、運用環境の DuckDB バージョン差異に注意。
- 一部内部関数（_call_openai_api 等）はテストのため patch 可能にしている。
- 初期リリースのため追加機能（PBR・配当利回り等のバリュー指標、strategy/execution の具体的なアルゴリズム）は今後の実装予定。

---

配布・改善履歴はこの CHANGELOG に追記していきます。問題報告や改善提案は issue を作成してください。