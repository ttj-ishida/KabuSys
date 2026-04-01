# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
今後のバージョンは「Unreleased」→ リリース日付きのバージョンへ移動してください。

## [Unreleased]
- （今後の変更をここに記載）

## [0.1.0] - 2026-04-01
初回リリース。日本株のデータ収集・研究・AIセンチメント・市場レジーム判定・カレンダー管理・ETLパイプラインを含む基本機能を実装。

### Added
- パッケージ基盤
  - パッケージ名: kabusys、バージョン 0.1.0 を設定。
  - 公開インターフェース: data, strategy, execution, monitoring を __all__ でエクスポート。

- 設定管理 (kabusys.config)
  - .env ファイル／環境変数の自動読み込み機能を実装（優先順位: OS 環境変数 > .env.local > .env）。
  - プロジェクトルートの検出ロジック（.git または pyproject.toml を親ディレクトリから探索）を導入。
  - .env パーサー: export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、インラインコメントの扱いなどを実装。
  - 上書き制御（override）と「保護された」OS環境変数の扱いに対応。
  - Settings クラスを提供（J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / 環境フラグ等）。必須環境変数未設定時は ValueError を送出。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動読み込みを無効化できる。

- AI モジュール (kabusys.ai)
  - news_nlp
    - raw_news と news_symbols テーブルを参照し、指定ウィンドウ（前日15:00 JST〜当日08:30 JST）内のニュースを銘柄単位に集約。
    - OpenAI（gpt-4o-mini / JSON Mode）へバッチ送信し銘柄ごとのセンチメント（-1.0〜1.0）を取得。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄）、1銘柄あたり記事数・文字数上限（デフォルト 10 件 / 3000 文字）を実装。
    - API 失敗（429 / ネットワーク / タイムアウト / 5xx）に対する指数バックオフリトライを実装。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results キー、コード整合性、数値チェック）、スコアの ±1.0 クリップを実装。
    - DuckDB への書き込みは冪等性を考慮（取得済みコードのみ DELETE → INSERT）し、部分失敗時に他銘柄スコアを保護。
    - テスト容易性のため _call_openai_api の差し替えを想定。

  - regime_detector
    - ETF 1321（Nikkei 225 連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次で判定。
    - マクロニュースはキーワードフィルタ（日本／米国系の主要語）で抽出し、OpenAI（gpt-4o-mini）へ送り JSON で macro_sentiment を取得。
    - MA 計算は target_date 未満のデータのみを使用し、ルックアヘッドバイアスを回避。
    - API 失敗時は macro_sentiment を 0.0 にフォールバックするフェイルセーフ実装。
    - DB へは冪等的に BEGIN / DELETE / INSERT / COMMIT で書き込み、失敗時は ROLLBACK を試行してエラーを上位へ伝播。

- 研究・特徴量モジュール (kabusys.research)
  - factor_research
    - モメンタム: 1M/3M/6M リターン、200 日 MA 乖離を計算する calc_momentum を実装。データ不足時には None を返す。
    - ボラティリティ/流動性: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算する calc_volatility を実装。true range の NULL 伝播や窓サイズチェックを含む。
    - バリュー: raw_financials から最新財務を取得し PER / ROE を計算する calc_value を実装。
    - DuckDB 上の SQL ウィンドウ関数を活用し、prices_daily / raw_financials のみを参照。

  - feature_exploration
    - 将来リターン calc_forward_returns（任意ホライズン、入力検証あり）。
    - IC（Spearman）計算 calc_ic（None 値や十分なサンプルがない場合の扱いを実装）。
    - ランク変換ユーティリティ rank（タイ同順位は平均ランク）。
    - 統計サマリー factor_summary（count/mean/std/min/max/median を算出）。
    - 標準ライブラリのみで実装（pandas 等に依存しない設計）。

- データプラットフォーム (kabusys.data)
  - calendar_management
    - market_calendar テーブルを用いた営業日判定ロジックを実装（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）。
    - DB にデータがある場合は DB 値優先、未登録日は曜日ベースでフォールバックする一貫した挙動。
    - calendar_update_job を実装。J-Quants API（jquants_client）から差分取得し、バックフィル・健全性チェックを行って保存する。
    - 最大探索範囲やバックフィル日数、異常検知ロジックを導入。

  - pipeline / etl
    - ETLResult データクラスを公開（kabusys.data.etl から再エクスポート）。ETL の取得数・保存数・品質問題・エラー集約をサポート。
    - ETL パイプラインの設計に基づくユーティリティ（差分取得、バックフィル、品質チェック連携）を実装（pipeline モジュール）。

- テスト支援
  - OpenAI 呼び出し箇所での差し替え（patch）を想定した設計（テスト時に _call_openai_api をモック可能）。

### Changed
- 新規初版のため該当なし。

### Fixed
- 新規初版のため該当なし。

### Security
- 環境変数の取り扱いに注意:
  - 必須トークン等は Settings で _require され、未設定時は ValueError を送出（誤ったデプロイ防止）。
  - .env の自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。

### Known issues / Notes
- pipeline._get_max_date の実装末尾が不完全に見える箇所が存在します（ソース末尾に不完全な戻り値表現あり）。初期リリース時は確認・修正が必要です。
- data/__init__.py は現状空で、jquants_client 等外部依存モジュールが必要（データ取得機能の実行には jquants_client の実装が前提）。
- OpenAI API を利用する機能（news_nlp, regime_detector）は API キー（OPENAI_API_KEY）が必要。実運用ではレート制限やコスト管理に注意してください。
- 日時の扱い:
  - ニュースウィンドウ等は UTC naive datetime を用いており、JST↔UTC の変換ロジックに基づいています。
  - ルックアヘッドバイアス防止のため、datetime.today()/date.today() を直接参照しない設計方針が採られています（一部ジョブは date.today() を使用）。

---

（補足）リリース後の運用推奨:
- OpenAI 呼び出しのログ/エラー監視を行い、レート制限や API エラー時の挙動を確認してください。
- DuckDB スキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials など）が前提となるため、初期セットアップ手順やスキーマ定義をドキュメント化してください。