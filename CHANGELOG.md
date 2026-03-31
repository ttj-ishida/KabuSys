Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを採用します。

[Unreleased]
------------

（現在未リリースの変更はありません）

[0.1.0] - 2026-03-31
-------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージ公開情報:
    - src/kabusys/__init__.py にて __version__ = "0.1.0" を定義。
    - パッケージ API として data, strategy, execution, monitoring をエクスポート。
- 環境設定管理
  - src/kabusys/config.py を追加。
  - .env ファイルまたは環境変数から設定読み込みを自動化（OS > .env.local > .env の優先順）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
  - .env パーサ実装（export 形式対応、クォート/エスケープ、インラインコメント処理）。
  - Settings クラスを提供し、各種必須設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）と補助設定（データベースパス、環境種別、ログレベル判定、is_live/is_paper/is_dev）を取得可能に。
  - 不正な KABUSYS_ENV / LOG_LEVEL 値は ValueError で明確にエラー化。
- AI 関連
  - src/kabusys/ai/news_nlp.py を追加
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）で銘柄別センチメント（ai_scores）を算出し ai_scores テーブルへ書き込み。
    - バッチ処理、チャンクサイズ制御、トークン肥大化対策（記事数・文字数トリム）、JSON Mode のバリデーション、429/ネットワーク/5xx に対する指数バックオフリトライを実装。
    - レスポンスの堅牢なパースと検証（未知コード無視、±1.0 クリップ、部分失敗時は既存スコア保護のため対象コードのみ置換）。
    - calc_news_window 関数で JST ベースのニュース収集ウィンドウを計算。
  - src/kabusys/ai/regime_detector.py を追加
    - ETF 1321 の 200 日移動平均乖離（70% 重み）とマクロニュースの LLM センチメント（30% 重み）を合成して日次市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - OpenAI 呼び出しの再試行・フェイルセーフ（API失敗時は macro_sentiment=0.0）やレスポンスパース保護を実装。
    - 内部で datetime.today()/date.today() を参照しない設計（ルックアヘッドバイアス防止）。
- Data / ETL / カレンダー / ジョブ
  - src/kabusys/data/pipeline.py を追加
    - ETLResult データクラス（ETL 実行結果の集約）を定義し公開。
    - 差分取得、バックフィル、品質チェック方針を実装するためのユーティリティを備える。
  - src/kabusys/data/etl.py で ETLResult を再エクスポート。
  - src/kabusys/data/calendar_management.py を追加
    - market_calendar の夜間バッチ更新ロジック（calendar_update_job）を実装。J-Quants クライアントを通じて差分取得 → 保存（ON CONFLICT）を行う。
    - 営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。DB 未取得時は曜日ベースでフォールバック。
    - 最大探索幅やバックフィル日数、健全性チェック等を実装して安全性を確保。
- Research モジュール
  - src/kabusys/research/factor_research.py を追加
    - Momentum（1M/3M/6M）、MA200 乖離、Volatility（ATR20）、Liquidity（20日平均売買代金/出来高比率）、Value（PER/ROE）などのファクター計算を実装。
    - DuckDB を使った SQL ベースの実装で prices_daily / raw_financials のみを参照。
    - データ不足時の None 扱いなど堅牢性を担保。
  - src/kabusys/research/feature_exploration.py を追加
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク変換（rank）、統計サマリー（factor_summary）を提供。
    - pandas など外部依存を排し、標準ライブラリ + DuckDB で実装。
  - src/kabusys/research/__init__.py で主要関数をエクスポート（calc_momentum, calc_value, calc_volatility, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。
- データユーティリティ
  - src/kabusys/data/__init__.py を追加（モジュールプレースホルダ）。
- テスト・開発を想定した設計上の考慮
  - OpenAI 呼び出しを _call_openai_api で抽象化して unittest.mock.patch による差し替えを想定。
  - DuckDB の executemany に関するバージョン制約（空リスト不可）を考慮した分岐を実装。
  - ルックアヘッドバイアス回避のため、target_date を引数に取り内部で現在時刻を参照しない実装方針を採用。

Changed
- （初版のため特段の変更履歴なし）

Fixed
- （初版のため特段の修正履歴なし）

Removed
- （初版のため特になし）

Security
- API キー・秘密情報の取り扱いに注意する旨の設計（環境変数から取得）。.env を誤って公開しないこと。

Notes / 既知の制限・運用メモ
- 必須環境変数
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（関数呼び出しで api_key が明示されない場合）
- .env 読み込みの挙動
  - OS 環境変数を保護（.env の上書き防止）しつつ .env.local は上書き可能（override=True）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを停止可能。
- OpenAI
  - gpt-4o-mini を前提とした JSON Mode を利用。APIエラー時はリトライ・フォールバック（0.0）とするため、完全な失敗があっても処理は続行される設計。
  - レスポンスの形式が期待と異なる場合は該当チャンクをスキップして他の銘柄への影響を最小化する。
- DuckDB
  - 一部実装で executemany の空リストを避けるチェックを追加（DuckDB 0.10 対応）。
- ルックアヘッドバイアス
  - すべての分析/スコアリング関数は target_date を明示的に受け取り、内部で現在日を参照しない設計。過去データのみを利用することでデータリークを防止。
- フェイルセーフ設計
  - マクロセンチメントやニューススコアの API 失敗時は 0.0 を用いるなど、上位処理が致命的に停止しない設計を採用。

マイグレーション / 使用開始メモ
- 初期導入時に期待される DB スキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等）を作成してください。
- OpenAI の API キーが必要です。テスト時は関数の _call_openai_api をモックしてください。
- .env.example を参照して必須の環境変数を設定してください。

開発者向け補足
- OpenAI 呼び出しのリトライやレスポンスパース処理は冪等性・部分失敗耐性を重視しているため、外部 API の不安定性を想定した運用が可能です。
- 各モジュールは DuckDB 接続を外部から受け取る設計（副作用を抑制）でテストが容易です。

（以上）