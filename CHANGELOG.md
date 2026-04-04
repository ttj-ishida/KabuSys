# Changelog

すべての変更は Keep a Changelog に準拠します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

[Unreleased]
- 計画中の改善:
  - ニュース / レジーム判定の OpenAI モデルやプロンプト最適化
  - PBR・配当利回り等のバリュー指標拡張
  - 単体テストの拡充（外部 API のモック化を含む）
  - ETL の並列化・パフォーマンス改善

[0.1.0] - 2026-04-04
Added
- パッケージ初期リリース: kabusys v0.1.0
  - モジュール構成:
    - kabusys.config: 環境変数 / .env 管理
      - プロジェクトルート（.git または pyproject.toml）を基点に .env/.env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
      - export プレフィックス、クォート付き値、インラインコメント等の .env パーシングに対応。
      - OS 環境変数を保護する protected 値の上書き制御。
      - 必須環境変数チェック（_require）と各種設定プロパティ（J-Quants / kabuAPI / LINE / DB パス / 監視閾値 / 環境判定 / ログレベル等）を提供。
      - KABUSYS_ENV と LOG_LEVEL のバリデーションを実装（無効値は ValueError）。
    - kabusys.ai.news_nlp: ニュースを用いた銘柄別 NLP スコアリング
      - 前日 15:00 JST 〜 当日 08:30 JST 相当のウィンドウ（UTC で変換）を対象に raw_news と news_symbols を集約。
      - 1 銘柄あたり最大記事数・最大文字数でトリムし、最大 20 銘柄 / バッチで OpenAI（gpt-4o-mini）へ送信。
      - JSON Mode でのレスポンス検証、部分失敗時の部分書き換え（DELETE → INSERT）により既存データを保護。
      - レート制限・ネットワーク断・5xx に対する指数バックオフのリトライ、その他エラーはフェイルセーフによりスキップ。
      - スコアは ±1.0 にクリップ。返却値は書き込んだ銘柄数。
      - calc_news_window: ターゲット日に対するニュース収集ウィンドウを返すユーティリティを提供。
    - kabusys.ai.regime_detector: 市場レジーム判定
      - ETF 1321（日経連動）の 200 日 MA 乖離（重み 70%）とマクロニュース（LLM センチメント、重み 30%）を合成して日次レジーム（bull/neutral/bear）を算出。
      - prices_daily / raw_news を参照し、OpenAI (gpt-4o-mini) を用いたマクロセンチメント評価を実行（記事が無ければ LLM 呼び出しを行わず 0.0）。
      - API 呼出し失敗時はマクロセンチメントを 0.0 として継続（フェイルセーフ）。
      - レジーム結果は market_regime テーブルへ冪等的に書き込む（BEGIN / DELETE / INSERT / COMMIT）。DB 書込み失敗時はロールバック。
      - LLM 呼出しは独立実装でモジュール結合を避ける設計（テスト容易性）。
    - kabusys.research: ファクター計算 & 特徴量探索
      - factor_research:
        - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None）を計算。
        - calc_volatility: 20 日 ATR（平均）、相対 ATR、20 日平均売買代金、出来高比率を計算。
        - calc_value: raw_financials から最新財務（target_date 以前）を取得し PER / ROE を計算（EPS=0/欠損は None）。
        - すべて DuckDB クエリベースで外部 API に依存しない（研究用に安全）。
      - feature_exploration:
        - calc_forward_returns: 指定 horizon（営業日）に対する将来リターンを一括取得。
        - calc_ic: スピアマンランク相関（IC）を計算（有効レコードが 3 件未満で None）。
        - rank / factor_summary: ランク化（同順位の平均ランク）と統計サマリーを提供。
        - pandas 等の外部依存を避け、標準ライブラリ + DuckDB で実装。
    - kabusys.data: データ基盤ユーティリティ
      - calendar_management:
        - JPX カレンダー管理（market_calendar）と営業日判定ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
        - DB 登録値を優先し、未登録日は曜日ベースでフォールバック（週末除外）。最長探索を _MAX_SEARCH_DAYS で制限して無限ループ回避。
        - calendar_update_job: J-Quants から差分取得 → 冪等保存（ON CONFLICT DO UPDATE）、バックフィルと健全性チェックを実装。
      - pipeline / etl:
        - ETLResult データクラスを公開（取得数・保存数・品質問題・エラーの集約）。
        - 差分更新・backfill・品質チェック（quality モジュール連携）を想定した ETL 基盤。id_token 注入などテストフレンドリーな設計。
      - jquants_client のラッパーを通じた差分取得・保存フローを想定（save_* の Idempotent 保存を前提）。
    - パッケージメタ:
      - __version__ = "0.1.0"
      - __all__ に主要パッケージ名を公開（data, strategy, execution, monitoring）

Changed
- 初期リリースの設計上の重要判断（ドキュメント化）
  - ルックアヘッドバイアス防止: 各処理は内部で datetime.today() / date.today() を参照しない（target_date を明示受け渡し）。
  - DuckDB への書き込みは部分失敗を考慮した実装（書き換え対象コードを限定する等）で、既存データの喪失を抑制。
  - OpenAI 呼び出しはリトライやレスポンスの厳密バリデーション（JSON 再抽出等）により堅牢化。

Fixed
- （該当なし）初回公開バージョンのため、既知の不具合修正はなし。

Deprecated
- （該当なし）

Removed
- （該当なし）

Security
- 環境変数取り扱い:
  - .env 自動読み込み時に OS 環境変数を保護（既存のプロセス環境を上書きしない設定がデフォルト）。
  - 必須の機密情報（OpenAI / J-Quants / kabuAPI パスワード等）は未設定時にエラーを上げる（明示的な通知）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD によりテスト時など自動ロードを抑制可能。

注記
- 本リリースは「研究・バックテスト」「データ基盤」「AI ベースのニュース解析・レジーム判定」を主目的とした初期機能群の公開です。  
  - 発注（実際の売買）に関するモジュールは本バージョンでは設計上分離されているか、実行系の実装（execution）については本CHANGELOGの記載箇所に依存する実装に留意してください。
  - OpenAI / J-Quants 等の外部 API 呼び出し箇所は、実行時に適切な API キーと料金設定が必要です。

---
メンテナンス履歴はコードベースから推測して作成しています。必要に応じて日付・詳細・追加の変更点を編集してください。