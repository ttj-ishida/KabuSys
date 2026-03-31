Keep a Changelog 準拠

すべてのバージョンはセマンティックバージョニングに従います。  
主な変更カテゴリ: Added, Changed, Fixed, Security, Removed（該当なしは省略）。

Unreleased
- 今後の変更を記載するプレースホルダです。

[0.1.0] - 2026-03-31
Added
- パッケージ初回リリース。以下の主要コンポーネントを追加。
  - kabusys.config
    - .env ファイルと環境変数の自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
    - .env/.env.local の読み込み順序を考慮。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - export KEY=val 形式、クォート・エスケープ、インラインコメント等に対応した .env パーサー実装。
    - 必須環境変数取得時に未設定なら ValueError を送出する _require ユーティリティ。
    - 設定オブジェクト Settings を公開。主要な設定項目:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
      - KABUSYS_ENV（development/paper_trading/live の検証）
      - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
      - DUCKDB_PATH / SQLITE_PATH のデフォルトパス設定
  - kabusys.ai
    - news_nlp モジュール: ニュース記事を集約して OpenAI（gpt-4o-mini）へ送信、銘柄ごとのセンチメント（ai_scores）を生成して DuckDB に書き込む。
      - ニュースウィンドウは JST ベース（前日15:00～当日08:30）、calc_news_window を提供。
      - 1 チャンク最大 20 銘柄、1 銘柄あたり最大 10 記事／3,000 文字のトリム。
      - JSON Mode 応答のバリデーションとフォールバック（余分な前後テキストから最外の {} を抽出）。
      - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ。
      - テスト用に _call_openai_api をパッチ差し替え可能に設計。
      - DuckDB 互換性のため、部分成功でも他銘柄の既存スコアを消さない DELETE → INSERT の置換ロジック。
    - regime_detector モジュール: ETF 1321（225 連動型）の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出し market_regime テーブルへ保存。
      - MA 計算は target_date 未満のデータのみを使用してルックアヘッドを防止。
      - LLM 呼出しは失敗時に macro_sentiment=0.0 へフォールバック（フェイルセーフ）し、最大リトライ回数を持つ。
      - レジーム合成はクリップ処理を行い閾値でラベル化。
      - 書き込みはトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等性を担保し、失敗時は ROLLBACK を試行。
  - kabusys.data
    - calendar_management: JPX カレンダー管理（market_calendar）と営業日判定ユーティリティを実装。
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days など。
      - DB にカレンダー情報がない場合は曜日ベースでフォールバック（土日非営業）。
      - calendar_update_job：J-Quants API から差分取得して market_calendar を冪等的に保存。バックフィルと健全性チェック実装。
    - pipeline / etl: ETL パイプラインインターフェースと ETLResult クラスを提供。
      - 差分更新ロジック、バックフィル、品質チェック（quality モジュール参照）を想定した設計。
      - ETLResult は監査ログ用変換を提供し、品質チェックの重大度検出を判定するユーティリティを持つ。
    - ETL 周辺の内部ユーティリティ（テーブル存在チェック、max date 取得など）。
    - jquants_client を通じたデータ取得／保存処理を想定（実際のクライアントは data.jquants_client で分離）。
  - kabusys.research
    - factor_research: Momentum / Value / Volatility / Liquidity 等のファクター計算関数を追加。
      - calc_momentum: 1M/3M/6M リターン、MA200 乖離（データ不足時は None／MA200 未満は None）。
      - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率等。
      - calc_value: raw_financials から EPS/ROE を取得して PER/ROE を計算（EPS が 0 の場合は None）。
      - DuckDB の SQL ウィンドウ関数を活用した実装。
    - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク関数（rank）、ファクター統計サマリー（factor_summary）を実装。
      - calc_forward_returns は任意ホライズン（デフォルト [1,5,21]）に対応、入力検証を実施。
      - calc_ic はスピアマンのランク相関を計算（有効レコードが 3 未満で None を返す）。
      - rank は同順位を平均順位で扱う実装。
  - パッケージトップレベル
    - kabusys.__version__ を "0.1.0" に設定し、主要サブパッケージを __all__ で公開。

Changed
- 初版リリースのため該当なし（初回追加のみ）。

Fixed
- 初版リリースのため該当なし。

Security
- 初版リリースのため該当なし（ただし環境変数に API キー等を保持する想定。公開レポジトリ等での取り扱いに注意）。

Notes / 実装上の重要点（利用者・開発者向け）
- Look-ahead バイアス防止:
  - AI スコアやファクター計算は datetime.today() / date.today() を参照せず、明示的な target_date を受け取る設計。
  - DB クエリは target_date を基準にして未来データを参照しないよう注意している。
- OpenAI 統合:
  - gpt-4o-mini / JSON Mode を想定。429 やネットワーク障害、5xx に対して再試行ロジックを実装。
  - レスポンスパース失敗や API 全消費時はフェイルセーフとしてスコア 0.0 を採用（例外を上位へ上げず継続）。
  - テスト容易性のため _call_openai_api をモック可能。
- DuckDB 互換性:
  - executemany における空リスト制約（DuckDB 0.10 等）を考慮して、書き込み前の空チェックを行う。
  - 一部 SQL では ROW_NUMBER / WINDOW 関数を多用しているため古い DuckDB バージョンとの互換性に注意が必要。
- トランザクション安全性:
  - market_regime / ai_scores 等は DELETE → INSERT をトランザクション内で行い、例外時に ROLLBACK を試行する実装。
- 環境設定:
  - 必須環境変数が未設定の場合は早期に ValueError を返すことで誤動作を防ぐ。
  - .env パーサーはクォートやエスケープを考慮しており、インラインコメント処理も行う。
- デフォルト値:
  - KABUSYS_ENV は "development" デフォルト、LOG_LEVEL は "INFO" デフォルト。
  - DUCKDB_PATH と SQLITE_PATH のデフォルトパスを提供。

既知の制限・今後の改善候補
- OpenAI のモデルハンドリング・レスポンス形式は将来の SDK 変更により調整が必要になる可能性がある（status_code の取得は getattr で安全化済み）。
- 一部の外部クライアント（jquants_client）や quality モジュールの具体実装は別モジュールに委譲しているため、本リポジトリ外の実装との連携検証が必要。
- JSON Mode のパースで前後ノイズを抽出するロジックは限定的。より堅牢な復元処理やスキーマバリデーションの強化を検討。

索引（主要 API）
- 設定: kabusys.config.settings
- ニューススコア: kabusys.ai.score_news(conn, target_date, api_key=None)
- レジーム判定: kabusys.ai.score_regime(conn, target_date, api_key=None)
- ETL 結果: kabusys.data.etl.ETLResult
- カレンダー: kabusys.data.calendar_management.is_trading_day / next_trading_day / calendar_update_job
- 研究用: kabusys.research.calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary

以上。