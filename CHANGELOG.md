# Changelog

すべての重要な変更を記録します。本ファイルは Keep a Changelog の形式に準拠しています。  

現在のバージョン: 0.1.0

## [0.1.0] - 2026-03-31

初回リリース（ベース実装）。以下の主要機能・モジュールを追加しました。

### 追加 (Added)
- パッケージ基盤
  - パッケージ名: kabusys、バージョン: 0.1.0（src/kabusys/__init__.py）。
  - 公開モジュール: data, strategy, execution, monitoring を __all__ で定義。

- 設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を自動読み込み（プロジェクトルート検出: .git または pyproject.toml）。
  - 読み込み順序: OS 環境 > .env.local（上書き）> .env（未設定時に設定）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用途）。
  - .env パーサーの実装:
    - export KEY=val 形式対応、クォート（'"/"）とエスケープ対応、インラインコメントの適切な扱い。
    - 無効行（空行、#で始まる行、等）をスキップ。
  - 必須環境変数取得ヘルパー (_require) と Settings クラス提供。
  - 必須項目（例）: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID。
  - 設定検証:
    - KABUSYS_ENV の許容値: development / paper_trading / live。
    - LOG_LEVEL の許容値: DEBUG / INFO / WARNING / ERROR / CRITICAL。
  - デフォルトのデータベースパス: DUCKDB_PATH, SQLITE_PATH。

- AI モジュール (src/kabusys/ai/)
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約し、銘柄ごとに OpenAI（gpt-4o-mini）へバッチ評価して ai_scores テーブルへ保存。
    - タイムウィンドウ（前日15:00 JST ～ 当日08:30 JST）計算ユーティリティ calc_news_window を提供。
    - バッチ処理: 最大 20 銘柄／回、1銘柄あたり記事最大10件・最大3000文字にトリム。
    - JSON Mode を利用した厳密な JSON 出力期待とレスポンスバリデーション実装。
    - リトライ戦略: 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ（デフォルト retry 上限）。
    - 失敗時のフェイルセーフ: API 失敗やパース失敗は該当チャンクをスキップし、他銘柄処理を継続。
    - DuckDB の executemany の制約（空リスト不可）を考慮して安全に DELETE → INSERT を実施。
    - パブリック API: score_news(conn, target_date, api_key=None)（OpenAI API キー必須、環境変数 OPENAI_API_KEY も参照）。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次レジーム判定（bull/neutral/bear）を算出。
    - マクロ記事の抽出は news_nlp.calc_news_window を利用。最大20記事を対象に gpt-4o-mini で macro_sentiment を評価。
    - レジームスコア合成式、閾値設定（BULL/BEAR）、および market_regime テーブルへの冪等書き込みを実装（BEGIN/DELETE/INSERT/COMMIT と ROLLBACK 対応）。
    - API 呼び出し失敗時は macro_sentiment = 0.0 にフォールバックして継続。
    - パブリック API: score_regime(conn, target_date, api_key=None)（OpenAI API キー必須）。

- データプラットフォーム / ETL（src/kabusys/data/）
  - ETL インターフェース再公開: ETLResult を kabusys.data.etl 経由でエクスポート。
  - ETL パイプライン結果モデル（src/kabusys/data/pipeline.py）
    - ETLResult dataclass（取得数・保存数・品質問題・エラーなどを保持）。has_errors / has_quality_errors / to_dict を提供。
    - 差分取得ロジックのユーティリティ（テーブル存在確認、最大日付取得等）。
    - 市場カレンダーヘルパーやバックフィル方針など設計に準拠した処理方針を実装。
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルに基づく is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - DB 未取得時は曜日ベースのフォールバック（週末除外）を採用し、一貫性を保持。
    - calendar_update_job: J-Quants からの差分フェッチと保存処理（バックフィル、健全性チェック、例外ハンドリング）を実装。
  - jquants_client と quality モジュールと連携する ETL フローを想定（fetch/save 関数呼び出し）。

- 研究 (research) モジュール（src/kabusys/research/）
  - factor_research（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン・200日MA乖離）、Volatility（20日 ATR 等）、Value（PER/ROE）などのファクター計算関数を実装。
    - DuckDB の SQL+ウィンドウ関数を用いた効率的な集計。データ不足時は None を返す設計。
    - パブリック関数: calc_momentum, calc_volatility, calc_value。
  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク付けユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - Spearman（ランク）相関に基づく IC 計算、少数データ時の None ハンドリングなどを実装。
  - データ正規化ユーティリティを kabusys.data.stats から再利用（zscore_normalize を __init__ で公開）。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- トランザクション保護:
  - データ書き込み（ai_scores, market_regime 等）で BEGIN/COMMIT/ROLLBACK を正しく扱う実装により、部分失敗時の DB 整合性を確保。
  - ROLLBACK が失敗した場合の警告ログ出力を追加。

### 注意事項 / 既知の設計方針
- AI 機能（score_news, score_regime）は OpenAI API キーが必須（api_key 引数 または 環境変数 OPENAI_API_KEY）。
- 時刻・日付の扱い:
  - ルックアヘッドバイアス防止のため、内部で datetime.today() / date.today() を参照しない設計（target_date の明示的指定を想定）。
  - raw_news.datetime は UTC 前提。ニュースウィンドウは JST 指定を UTC に変換して比較する。
- フェイルセーフ:
  - API 呼び出し失敗は可能な限りスキップ/フォールバック（macro_sentiment=0.0 等）してパイプライン全体を停止させない方針。
- DuckDB 互換性:
  - executemany に空リストを渡すと失敗する制約を考慮した実装（事前チェックを実施）。
- .env パーサーは多くのフォーマット（export, クォート、インラインコメント）に対応しているが、特殊なケースでは期待どおりに解析できない可能性あり。

### セキュリティ (Security)
- （初回リリースのため既知のセキュリティ修正は無し）
- 注意: 実行時設定値（API トークン等）は環境変数または .env に格納する設計。運用時は適切なシークレット管理を推奨。

---

今後のリリースでは以下を予定しています（案）
- strategy / execution / monitoring の具象実装（注文ロジック、実行エンジン、監視・通知機能）の追加
- 単体テスト・統合テストの拡充、CI パイプライン整備
- 性能最適化と大規模データ対応（バッチ設計・並列化等）
- セキュリティ監査・シークレット管理の強化

（必要があれば、各関数やモジュールの詳細な変更点や理由を追記します。）