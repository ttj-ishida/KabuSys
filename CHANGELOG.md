CHANGELOG
=========

すべての変更は Keep a Changelog 準拠で記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

[Unreleased]
-------------

- （現時点では未リリースの変更はありません）

[0.1.0] - 2026-03-28
-------------------

Added
- パッケージ初回リリース (kabusys 0.1.0)
  - プロジェクト概要: 日本株自動売買システムの基盤ライブラリを提供。
  - モジュール構成:
    - kabusys.config
      - .env ファイルまたは環境変数からの設定読み込み機能を実装。
      - 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に探索。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD を設定することで自動ロードを無効化可能。
      - .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いに対応。
      - _load_env_file は既存 OS 環境変数を保護する protected 引数をサポート（override 動作の制御）。
      - Settings クラスを提供し、必要な環境変数の必須チェック（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）と既定値（KABU_API_BASE_URL、DBパス等）を管理。
      - KABUSYS_ENV と LOG_LEVEL の値検証（許容値チェック）を実装。
    - kabusys.data
      - calendar_management
        - JPX カレンダー管理と営業日判定ユーティリティを実装（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
        - market_calendar が未取得の場合は曜日ベースのフォールバックを行う実装。
        - calendar_update_job: J-Quants から差分取得して冪等的に保存する夜間バッチ処理（バックフィル、健全性チェック含む）。
      - pipeline / etl
        - ETLResult データクラスを公開し、ETL の取得/保存件数、品質問題、エラー情報を集約。
        - 差分取得・バックフィル・品質チェックを想定した設計。
      - ETL インターフェース公開 (kabusys.data.etl -> ETLResult)
      - DuckDB を利用する前提での互換性考慮（例: executemany に対する空リスト回避等の実装上の注意）。
    - kabusys.ai
      - news_nlp
        - ニュース記事の銘柄別センチメントスコアリングを実装（OpenAI gpt-4o-mini の JSON モードを利用）。
        - JST 時刻ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を UTC に変換してDBの raw_news を抽出。
        - 1銘柄当たりの最大記事数／文字数でトリムする保護を実装。
        - バッチ（最大 20 銘柄）での API 呼び出し、指数バックオフによる再試行（429 / ネットワーク / タイムアウト / 5xx 対応）。
        - レスポンス検証ロジックを実装（JSON 抽出、"results" 構造、コード照合、数値検証、±1 クリップ）。
        - テスト容易性のため _call_openai_api を patch で差し替え可能に設計。
      - regime_detector
        - 市場レジーム判定ロジックを実装。ETF 1321 の 200 日移動平均乖離（重み70%）と、マクロニュースの LLM センチメント（重み30%）を合成して日次で 'bull'/'neutral'/'bear' を判定。
        - MA 計算は target_date 未満のデータのみを使用しルックアヘッドを防止。
        - マクロキーワードによる raw_news フィルタリング、OpenAI 呼び出し（JSON mode）によるセンチメント算出、合成スコアの閾値判定を実装。
        - API エラー時は macro_sentiment=0.0 としてフェイルセーフに復帰。
        - 冪等（BEGIN / DELETE / INSERT / COMMIT）で market_regime テーブルへ書き込み。
        - テスト容易性のため _call_openai_api をモック差替え可能。
    - kabusys.research
      - factor_research
        - モメンタム（1M/3M/6M リターン、200日MA乖離）、ボラティリティ（20日 ATR）、バリュー（PER/ROE）等の定量ファクターを DuckDB の prices_daily / raw_financials を用いて計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
        - データ不足時に None を返すことで安全に扱える設計。
        - パフォーマンス配慮のスキャン範囲バッファや窓計算を実装。
      - feature_exploration
        - 将来リターン計算（calc_forward_returns）: 任意ホライズン（デフォルト [1,5,21]）での fwd_* 計算。
        - IC（calc_ic）: Spearman（ランク相関）を実装し、最小有効レコード数をチェック。
        - ランク変換ユーティリティ（rank）: 同順位は平均ランクを返す実装。
        - 統計サマリー（factor_summary）: count/mean/std/min/max/median を計算。
      - 標準ライブラリのみでの実装を目指し、外部依存を排除。
    - ルートパッケージの __version__ = "0.1.0" を設定。

Changed
- n/a（初回リリースのため過去からの変更はなし）

Fixed
- n/a（初回リリースのため既存バグ修正履歴はなし）

Notes / Implementation details
- Lookahead バイアス対策: AI モジュールやファクター計算は target_date より未来のデータを参照しないよう厳密に設計。
- OpenAI 利用: gpt-4o-mini を JSON mode（response_format={"type":"json_object"}）で呼び出す前提。API エラー処理は 429/ネットワーク/タイムアウト/5xx を再試行、その他は安全にフェイルする設計。
- DuckDB 周り: executemany に空リストを渡すと失敗するバージョン互換問題に配慮した実装（空チェックを行う）。
- .env パーサの挙動:
  - export プレフィックス対応
  - シングル／ダブルクォート内部のバックスラッシュエスケープ対応
  - 非クォート値の '#' は直前が空白またはタブの場合のみコメント扱い
- テストしやすさ: OpenAI 呼び出しを内部関数 (_call_openai_api) に分離し、patch で差し替えられるように実装しているためユニットテストで外部 API をモック可能。
- 冪等性: ETL 保存処理や market_regime / ai_scores への書き込みは既存レコードを削除してから挿入することで部分失敗時に他データを保護するよう設計。

Known limitations / Future work
- 現バージョンでは PBR・配当利回りなどのバリュー指標は未実装（calc_value の注釈参照）。
- OpenAI レスポンスの構造や SDK 変更に対しては現在の実装である程度耐性を持たせているが、将来的な SDK 変更時の追加対応が必要になる可能性あり。
- jquants_client（外部依存）周りの具象実装は別モジュールに委譲しているため、API クライアント側の実装・例外処理によっては追加の保護が必要になることがある。

Authors
- kabusys チーム（コードベースに基づき推測して作成）

License
- プロジェクトのライセンス表記はソース外のためここでは省略。README や pyproject.toml を参照してください。