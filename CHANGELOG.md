# Changelog

すべての変更は「Keep a Changelog」規約に従って記載します。バージョン番号は src/kabusys/__init__.py の __version__ に合わせています。

全般的な注意
- 本リリースは初期公開版（0.1.0）に相当します。パッケージは DuckDB を内部データストアとして想定し、J-Quants / OpenAI（gpt-4o-mini）を外部依存として利用します。環境変数の設定（OpenAI / Slack / kabuAPI 等）が必須の機能があります。詳細は各モジュールの docstring を参照してください。

[Unreleased]
- （なし）

[0.1.0] - 2026-04-01
Added
- パッケージのコア構成を追加
  - モジュール公開: kabusys パッケージの基礎（__version__ = 0.1.0、公開サブパッケージ一覧）。
- 環境設定管理機能を追加 (kabusys.config)
  - .env/.env.local 自動読み込み機能（プロジェクトルートを .git / pyproject.toml で探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - .env パーサ実装: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理（クォート有無での違いを考慮）。
  - 上書き制御: .env と .env.local の優先度制御、既存 OS 環境変数を保護する protected セット。
  - Settings クラス: J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / ログレベル / 環境 (development/paper_trading/live) 等のプロパティを提供。未設定の必須環境変数は明示的に ValueError を送出。
- AI（自然言語処理）機能を追加 (kabusys.ai)
  - ニュースセンチメント: score_news (news_nlp)
    - ニュース収集ウィンドウ計算（JST 基準 → UTC 変換）。
    - raw_news と news_symbols を用いて銘柄毎に記事を集約（最大記事数・最大文字数でトリム）。
    - OpenAI（gpt-4o-mini）の JSON mode を用いたバッチ評価（チャンク単位で最大 20 銘柄）。
    - 再試行ロジック: 429・ネットワーク断・タイムアウト・5xx に対して指数バックオフでリトライ。
    - レスポンス検証: JSON の復元・results リスト検証、未知コード無視、スコアを ±1.0 にクリップ。
    - DB への冪等書き込み戦略: 成功した銘柄のみ DELETE → INSERT（部分失敗時に既存スコアを保護）。
    - テスト容易性: OpenAI 呼び出し箇所は内部関数に抽象化して patch 可能。
  - 市場レジーム判定: score_regime (regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム ('bull'/'neutral'/'bear') を判定。
    - prices_daily / raw_news からのデータ取得、OpenAI 呼び出し（gpt-4o-mini JSON mode）、API 失敗時は macro_sentiment=0.0 とするフェイルセーフ。
    - レジーム結果を market_regime テーブルへ冪等（BEGIN / DELETE / INSERT / COMMIT）で保存。
    - LLM 呼び出しは news_nlp と独立実装（モジュール結合回避、テスト性向上）。
- データ基盤機能を追加 (kabusys.data)
  - マーケットカレンダー管理 (calendar_management)
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を実装。
    - market_calendar が存在しない場合は曜日（週末）でフォールバックする堅牢なロジック。
    - カレンダーの夜間バッチ更新 calendar_update_job を実装（J-Quants クライアント経由の差分取得・バックフィル・健全性チェック）。
    - DB 登録値優先、未登録日は曜日フォールバック等、一貫性を重視した設計。
  - ETL パイプライン (pipeline, etl)
    - ETLResult データクラスを追加（取得数・保存数・品質問題・エラー集計等）。
    - pipeline モジュールの ETLResult を etl 経由で再エクスポート。
    - 差分更新、バックフィル、品質チェック（quality モジュールを想定）方針を記述した基盤コード。
- リサーチ機能を追加 (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターンと 200 日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務データを取得し PER / ROE を計算（EPS が 0/欠損の場合は None）。
    - 全関数は DuckDB の prices_daily / raw_financials のみを参照し、本番注文等の副作用なし。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
    - calc_ic: ファクターと将来リターンの Spearman ランク相関（IC）を計算。
    - rank: 同順位は平均ランクで扱うランク変換ユーティリティ。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
    - すべて標準ライブラリのみで実装（pandas 等に依存しない）。
- ロギングとエラー処理
  - 各主要処理で情報・警告・例外ログを出力し、外部 API のエラーはフェイルセーフ（スコア 0.0 またはスキップ）で処理を継続する設計。
  - DB 書き込み時はトランザクションを使用し、失敗時は ROLLBACK を試行してから上位に例外を伝播。

Changed
- 初版のため変更履歴はありません（新規追加のみ）。

Fixed
- 初版のため修正履歴はありません。

Security
- OpenAI API キーや Slack トークンなど必須の秘密情報は Settings が環境変数から取得し、未設定時には ValueError を送出。自動ロードされる .env ファイルは既存 OS 環境変数を保護する仕組みを持ちます。

Notes
- 必須環境変数:
  - OPENAI_API_KEY（score_news / score_regime 実行時）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等（各機能で使用）
- DuckDB スキーマ:
  - 本コードは prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等のテーブルを前提としています。初回実行前にスキーマを準備してください。
- テスト/モック:
  - OpenAI 呼び出し箇所（各モジュールの _call_openai_api）を unittest.mock.patch で差し替えることで API 依存のテストが容易です。
- 互換性・既知の制約:
  - DuckDB の executemany に空リストを渡せない（0.10 系）等の DB 側制約を扱うため保護コードを追加しています。
  - datetime.today() / date.today() を直接参照しない設計（ルックアヘッドバイアス防止）。API を含む処理は target_date を明示的に受け取ります。

今後の改善候補（未実装／検討中）
- ai_scores / market_regime / calendar のスキーマ定義・マイグレーションユーティリティの追加。
- monitoring サブパッケージの実装（パッケージ __all__ に名前はあるが実装は別途）。
- 追加の品質チェック・アラート機能（Slack 連携等）の拡充。
- より豊富なドキュメントと利用例（コマンドライン / ワーカージョブのサンプル）。

作者・貢献
- 初回リリース相当の実装をまとめて追加。機能ごとに詳細な docstring と設計メモを含めています。バグ報告・改善提案は Pull Request または Issue で受け付けてください。