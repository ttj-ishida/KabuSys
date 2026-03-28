Keep a Changelog 準拠 — 変更履歴 (日本語)
======================================

すべての重要な変更はこのファイルに記録します。フォーマットは Keep a Changelog に準拠しています。  
初回公開バージョンは 0.1.0 としてリリースしています。日付はコード解析時点（2026-03-28）です。

Unreleased
----------
（今後の変更をここに記載します）

[0.1.0] - 2026-03-28
-------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージ概要: 日本株自動売買システム用のライブラリ基盤を提供。
  - __version__ を "0.1.0" として公開。

- 設定 / 環境変数管理 (kabusys.config)
  - .env / .env.local ファイルおよび OS 環境変数からの設定自動読み込み機能を実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト用途）。
    - プロジェクトルートの検出は __file__ を起点に .git または pyproject.toml を探索（CWD 非依存）。
    - .env パーサは export プレフィックス・クォートやエスケープ・インラインコメント等に対応。
    - OS 環境変数は protected として上書き防止。
  - Settings クラスを提供:
    - J-Quants / kabu API / Slack / DB パス（DuckDB / SQLite）などのプロパティ取得。
    - env, log_level のバリデーション（許容値チェック）。
    - is_live / is_paper / is_dev のヘルパーを提供。
    - 必須変数未設定時は ValueError を送出。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (news_nlp.score_news)
    - raw_news / news_symbols を基に銘柄毎にニュースを集約し OpenAI (gpt-4o-mini) を用いてセンチメントを算出。
    - 時間ウィンドウ定義（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で提供（UTC 対応）。
    - 1銘柄あたり最大記事数・文字数トリム (_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK)。
    - バッチ処理（最大 20 銘柄/コール）と JSON Mode レスポンスの検証。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ実装。
    - レスポンス検証で未知コードを無視、数値変換不能はスキップ、スコアは ±1.0 にクリップ。
    - 書き込みは冪等性を考慮（対象コードのみ DELETE → INSERT）。DuckDB バージョン互換性対策あり（executemany 空リスト回避）。
    - API 呼び出しはテスト差し替え可能（_call_openai_api を patch して差し替え可能）。
  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離 (重み 70%) とニュース LLM センチメント (重み 30%) を合成して日次レジーム（bull/neutral/bear）を判定。
    - ma200_ratio の計算（target_date 未満のデータのみ使用しルックアヘッドを防止）。
    - マクロニュース抽出（定義済みマクロキーワード）→ LLM 評価 → 重み付け合成 → テーブル書込み（冪等的）。
    - LLM 呼び出しの失敗は macro_sentiment=0.0 としてフェイルセーフに処理。
    - OpenAI クライアント初期化は API キー注入可能（引数優先、未指定は OPENAI_API_KEY 環境変数を参照）。
    - API 呼び出し・再試行・エラー処理を備え、JSON パースエラーに対するロギングとフォールバックを実装。

- Data / ETL / カレンダー管理 (kabusys.data)
  - calendar_management モジュール
    - JPX カレンダー（market_calendar）を扱うユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録データがない場合は曜日ベース（土日休場）でフォールバック。DB 登録がある場合は DB 値優先、未登録日は曜日フォールバックで一貫性を保持。
    - 最大探索日数制限で無限ループ防止。
    - 夜間バッチ更新 job (calendar_update_job) を実装（J-Quants から差分取得→保存、バックフィル日数対応、健全性チェック）。
  - ETL パイプライン (pipeline.ETLResult ほか)
    - ETLResult データクラスを公開（取得数・保存数・品質問題・エラー一覧等を保持）。
    - 差分更新、バックフィル、品質チェックを行う設計方針を反映（jquants_client と quality モジュール連携想定）。
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得など。
    - 初期データ読み込み用の最小データ日付定数やバックフィル日数定義。

- 研究（Research）モジュール (kabusys.research)
  - factor_research:
    - モメンタム (calc_momentum): 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）。
    - ボラティリティ/流動性 (calc_volatility): 20 日 ATR、ATR 比率、平均売買代金、出来高比率。
    - バリュー (calc_value): raw_financials から EPS/ROE を取り、PER/ROE を算出（EPS が 0/欠損時は None）。
    - DuckDB を用いた計算、営業日を考慮したスキャン幅、データ不足時の None 処理。
  - feature_exploration:
    - 将来リターン計算 (calc_forward_returns): 複数ホライズン（デフォルト [1,5,21]）をサポート、引数バリデーションあり。
    - IC 計算 (calc_ic): ファクターと将来リターンのスピアマンランク相関を計算（有効データ不足時は None）。
    - ランク変換 (rank): 同順位は平均ランク、丸め処理で ties の対処。
    - 統計サマリー (factor_summary): count/mean/std/min/max/median を計算。
  - kabusys.research パッケージは kabusys.data.stats の zscore_normalize を再エクスポート。

Changed
- （初回リリースのため、既存機能の変更履歴はなし）

Fixed
- （初回リリースのため、修正履歴はなし）

Security
- API キーは Settings 経由で環境変数から取得する仕様。コード内に平文でハードコーディングしない設計。
- .env 自動ロードは明示的フラグで無効化可能（テスト・CI 用の安全機構）。

Notes / 設計上の重要点
- ルックアヘッドバイアス対策
  - 日付参照に datetime.today() / date.today() を直接使わない方針を明記。target_date ベースの計算・クエリで将来データ参照を避ける設計。
- フェイルセーフ
  - LLM/API 失敗時はスコアを 0.0 として継続するなど、致命的停止を避ける実装を採用。
- DuckDB 互換対策
  - executemany に空リストを渡さないなど、DuckDB の実装差分を考慮した互換性処理を実装。
- テスト容易性
  - OpenAI 呼び出し部分はモジュール内で分離されており、ユニットテストでパッチ差替え可能。
  - 環境自動ロードは無効化できるフラグを用意。

Known Issues / Limitations
- PBR・配当利回り等のバリューファクターは未実装（calc_value 注記）。
- strategy / execution / monitoring などトップレベル __all__ に含まれる一部サブパッケージは本リリースでの実装が限定的または未提供の可能性あり（将来追加予定）。
- OpenAI API の利用はコストとレイテンシの影響を受けるため、運用時は呼び出し頻度・バッチサイズのチューニングが必要。

Contributing
- バグ修正・機能追加・ドキュメント改善は Pull Request を通じて受け付けます。テストカバレッジと互換性に配慮してください。

ライセンス
- リポジトリ内の他のファイルやルートの LICENSE を参照してください（本 CHANGELOG にはライセンス情報の記載を含めていません）。