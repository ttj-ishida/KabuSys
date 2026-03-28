CHANGELOG
=========

すべての変更は Keep a Changelog のフォーマットに準拠して記載しています。
初期リリースの内容はコードベースから推測してまとめています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- （なし）

[0.1.0] - 2026-03-28
--------------------

Added
- パッケージ初期構成を追加
  - パッケージ名: kabusys（バージョン 0.1.0）
  - メインモジュールエクスポート: data, strategy, execution, monitoring

- 環境変数・設定管理モジュール (kabusys.config)
  - .env 自動読み込み機能を実装
    - 自動ロードはプロジェクトルート（.git または pyproject.toml を探索）を起点に行うため、CWD に依存しない設計
    - 読み込み順序: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能
    - OS 環境変数を保護する protected 機能を実装（.env.local の上書き制御等）
  - .env のパースを強化
    - export KEY=val 形式に対応
    - シングル／ダブルクォート内のバックスラッシュエスケープを正しく処理
    - インラインコメントの扱い（クォートあり/なしの差別化）
    - 無効行（空行・コメント・key=なし）を無視
  - Settings クラスでアプリ設定を公開
    - J-Quants / kabu ステーション / Slack / DB パス等のプロパティを提供
    - 必須値取得時の _require による明示的なエラー（未設定時は ValueError）
    - KABUSYS_ENV の許容値検証（development / paper_trading / live）
    - LOG_LEVEL の許容値検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev のヘルパープロパティ

- AI 関連モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news / news_symbols を読み、銘柄ごとにニュースを集約して OpenAI（gpt-4o-mini）へバッチ送信
    - チャンク処理: 最大 20 銘柄ずつ送信、1銘柄あたり最大記事数・最大文字数でトリム
    - レスポンスの堅牢なバリデーション（JSON 抽出/検証、未知コードの無視、数値変換、クリップ）
    - リトライ戦略: 429・ネットワーク断・タイムアウト・5xx に対して指数バックオフで再試行
    - フェイルセーフ: API 失敗時は当該チャンクをスキップして残りを継続（例外を上げずにログ出力）
    - 書き込みは冪等（該当コードのみ DELETE → INSERT）で部分失敗でも既存データを保護
    - calc_news_window: JST ベースのニュース収集ウィンドウ（前日 15:00 ～ 当日 08:30 JST）を算出するユーティリティ
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とニュースの LLM センチメント（重み 30%）を合成して
      market_regime テーブルへ日次で書き込み（ラベル: bull / neutral / bear）
    - ルックアヘッドバイアス対策: target_date 未満のデータのみを利用し、datetime.today()/date.today() を参照しない設計
    - OpenAI 呼び出しの独立実装（news_nlp と意図的に分離）
    - API エラーや JSON パース失敗時は macro_sentiment=0.0 にフォールバック（継続処理）
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）とトランザクションの失敗時は ROLLBACK を試行

- データ関連モジュール (kabusys.data)
  - ETL パイプライン (kabusys.data.pipeline)
    - ETLResult データクラスを導入（取得件数・保存件数・品質問題・エラー等を集約）
    - 差分取得・バックフィル・品質チェックを想定した設計（J-Quants API と連携）
    - DuckDB を前提とした最大日付検出やテーブル存在チェックなどのユーティリティを提供
  - ETL インターフェースの再エクスポート (kabusys.data.etl)
    - ETLResult を公開
  - マーケットカレンダー管理 (kabusys.data.calendar_management)
    - market_calendar を用いた営業日判定ユーティリティ群を実装
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB 値優先で未登録日は曜日ベースでフォールバックする一貫したロジック
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等保存（バックフィル・健全性チェックを含む）
    - 最大探索日数の制限や異常検知（将来日付の健全性チェック）により安全性を確保

- 研究用モジュール (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None）
    - Volatility / Liquidity: 20 日 ATR（平均）、相対 ATR、平均売買代金、出来高比
    - Value: PER（EPS が 0/欠損時は None）、ROE（raw_financials から取得）
    - DuckDB SQL を使った効率的な実装、外部 API へのアクセスは無し
  - 特徴量探索 (kabusys.research.feature_exploration)
    - 将来リターン calc_forward_returns（複数ホライズンに対応、入力検証あり）
    - IC（Information Coefficient）計算（スピアマンのランク相関）
    - ランク変換ユーティリティ rank（同順位は平均ランク）
    - 統計サマリー factor_summary（count/mean/std/min/max/median）

Changed
- （初回リリースのため変更履歴なし）

Fixed
- （初回リリースのため修正履歴なし）

Security
- OpenAI API キーの取り扱いについて
  - OpenAI を利用する機能（news_nlp / regime_detector）は api_key 引数または環境変数 OPENAI_API_KEY を参照
  - API キー未設定時は ValueError を送出して明示的にエラーにする
- 環境変数自動ロードはデフォルトで有効だが、KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能

Notes / Migration
- このリリースは「初期実装」と想定しています。以下に留意してください:
  - DuckDB を内部で使用するため、呼び出し側は接続（duckdb.DuckDBPyConnection）を渡す必要があります。
  - OpenAI のモデルはデフォルトで gpt-4o-mini を使用します（モデル指定はコード内定数で管理）。
  - .env の自動読み込みはプロジェクトルート検出に依存するため、配布後やテスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して明示的に制御してください。
  - AI モジュールのテスト容易性を考慮して、OpenAI 呼び出し箇所は差し替え可能（ユニットテストでの patch を想定）。
  - ai_scores / market_regime 等の DB 書き込みは冪等化されているため、再実行可能なバッチ処理が可能です。

連絡・貢献
- バグ報告や提案はIssueへお願いします（リポジトリの Issue ポリシーに従ってください）。