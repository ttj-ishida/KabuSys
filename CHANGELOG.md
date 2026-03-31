# Changelog

すべての重要な変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に従い、セマンティックバージョニングを使用します。

現在のバージョン: 0.1.0

## [Unreleased]

計画中 / 今後の作業（コードおよび設計から推測）
- strategy / execution / monitoring パッケージの具現化（現在 __all__ に宣言済みだが実体ファイルは未提供）
- 単体テストの拡充（OpenAI 呼び出しや J-Quants クライアントのモックを用いた網羅）
- ドキュメントの拡充（使用例、API 仕様、データベーススキーマの詳細）
- エラーハンドリング・メトリクスの改善（監視・アラート統合）
- DuckDB/SQL のバージョン依存性に対する互換性処理の追加

---

## [0.1.0] - 2026-03-31

初回リリース。以下の主要機能・モジュールを実装しました（コードの構成・実装から推測して記載）。

Added
- パッケージ基盤
  - kabusys パッケージ初期化（src/kabusys/__init__.py）。公開モジュールとして data, strategy, execution, monitoring を宣言。
  - バージョン番号を 0.1.0 に設定。

- 設定・環境変数管理（src/kabusys/config.py）
  - プロジェクトルート検出（.git または pyproject.toml）に基づく .env 自動読み込み機能を実装。
  - .env/.env.local の読み込み優先順位を実装（OS 環境 > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - .env パーサーの実装：export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメントの取り扱いに対応。
  - Settings クラスを提供し、必須設定の取得（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）や検証（KABUSYS_ENV, LOG_LEVEL）を行うユーティリティを提供。
  - デフォルト値の提供（KABU_API_BASE_URL, データベースパス, 監視閾値等）。

- AI モジュール（src/kabusys/ai）
  - news_nlp モジュール（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を使った銘柄ごとのニュース集約、OpenAI（gpt-4o-mini）によるバッチセンチメント評価を実装。
    - バッチ処理（最大 20 銘柄/回）、トークン肥大化対策（記事数上限・文字数トリム）を実装。
    - 再試行ロジック（429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ）とレスポンス検証（JSON 抽出・results 構造のバリデーション）を実装。
    - スコアは ±1.0 にクリップ。部分失敗時に既存スコアを保護するため、書き込みは対象コードのみ DELETE → INSERT を行う。
    - calc_news_window ユーティリティ（JST 時刻窓の UTC 変換）を実装。
    - テスト容易性のため OpenAI 呼び出し箇所を差し替え可能に実装（内部 _call_openai_api を patch 可能）。

  - regime_detector モジュール（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225 連動）の 200 日移動平均乖離（重み 70%）とニュースベースの LLM マクロセンチメント（重み 30%）を合成し、市場レジーム（bull/neutral/bear）を判定して market_regime テーブルへ冪等書き込みを行う。
    - マクロキーワードによる raw_news フィルタリング、OpenAI 呼び出し・リトライ・フォールバック（API 失敗時は macro_sentiment=0.0）を実装。
    - DB クエリはルックアヘッドバイアス対策が施されている（target_date 未満のデータのみ使用）。
    - こちらも OpenAI クライアント呼び出し点は差し替え可能に実装。

- データプラットフォーム（src/kabusys/data）
  - calendar_management（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを参照・更新することで営業日判定（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を提供。
    - DB 登録値優先、未登録日は曜日ベースのフォールバックを行う一貫したロジック。
    - JPX カレンダーを J-Quants から差分取得して冪等保存する calendar_update_job を実装（バックフィル・健全性チェック含む）。

  - ETL パイプライン（src/kabusys/data/pipeline.py / src/kabusys/data/etl.py）
    - ETLResult データクラスを公開（取得・保存件数、品質問題、エラー一覧を保持）。
    - 差分取得・保存・品質チェックの設計方針を実装（J-Quants クライアント経由で保存、バックフィルを考慮）。
    - etl モジュールは pipeline.ETLResult を再エクスポート。

  - データユーティリティ（calendar 管理で利用）:
    - テーブル存在チェック、DuckDB からの date 型変換ユーティリティ等を提供。

- Research（src/kabusys/research）
  - factor_research（src/kabusys/research/factor_research.py）
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金、出来高比）およびバリュー（PER, ROE）を DuckDB 上の prices_daily / raw_financials から計算する関数を実装。
    - データ不足時の None ハンドリングやログ出力、営業日バッファ設計を実装。

  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）算出（calc_ic）、ランク付けユーティリティ（rank）、統計サマリー（factor_summary）を実装。
    - 外部ライブラリに依存せず、標準ライブラリのみで統計計算を行う設計。
    - calc_forward_returns は horizons 検証（正の整数かつ <=252）やパフォーマンス上のスキャン範囲最適化を実装。

- 研究ユーティリティの再エクスポート（src/kabusys/research/__init__.py）
  - 主要関数（zscore_normalize, calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, rank）を公開。

- テスト・運用を意識した設計上の配慮
  - OpenAI 呼び出しを個別 private 関数に分離し、テスト時に patch しやすい設計。
  - ルックアヘッドバイアス防止のため、内部処理は datetime.today()/date.today() を参照しない設計（target_date を引数で指定）。
  - API エラー時は例外を投げずフォールバック（0.0 スコア等）する箇所が多数あり、フェイルセーフ性を重視。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Security
- .env の読み込みは OS 環境変数を上書きしないデフォルト動作で、.env.local による上書きをサポート。重要トークンの取り扱いに関する注意設計あり。

Notes / 実装上の注意（コードから読み取れる事項）
- DuckDB の executemany に空リストを渡せないバージョン互換性を考慮して、書き込み前に空判定を行う実装がある。
- OpenAI の API エラー型（status_code の有無など）に対して寛容に処理する実装がある（将来の SDK 変更への耐性）。
- calendar_update_job 等は外部 jquants_client（kabusys.data.jquants_client）を利用する想定で、実際の API 呼び出し・保存関数は別モジュールに委譲している。

---

メンテナンス: この CHANGELOG はコードベースの現状から推測して作成しています。実際のコミット履歴・設計ドキュメントと差分がある可能性があります。必要であれば実際の Git 履歴に基づく詳細な変更履歴に更新します。