Keep a Changelog
=================
このファイルは Keep a Changelog の形式に準拠しています。
新しい変更は上から追加してください。  
フォーマットについて: https://keepachangelog.com/ja/

Unreleased
---------
（なし）

[0.1.0] - 2026-03-31
-------------------
Added
- パッケージ初期リリース: kabusys 0.1.0 を追加。
  - パッケージ公開エントリポイント: kabusys.__init__.py にて __version__ = "0.1.0"、公開サブパッケージを定義（data, strategy, execution, monitoring）。
- 環境設定/ロード機能（kabusys.config）
  - .env / .env.local を自動ロード（プロジェクトルートは .git または pyproject.toml を起点に探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサ実装: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの判定ルールを実装。
  - 上書き（override）と保護（protected: OS 環境変数を保護）をサポートする .env 読み込みロジック。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス /監視閾値 / 環境（KABUSYS_ENV）/ログレベル検証（LOG_LEVEL）などをプロパティ経由で取得可能に。
  - KABUSYS_ENV と LOG_LEVEL の値検証（許容値外は ValueError）。
- AI モジュール（kabusys.ai）
  - news_nlp.score_news:
    - ニュース記事のタイムウィンドウ計算（JST ベースの前日 15:00 〜 当日 08:30 相当。内部は UTC naive datetime）。
    - raw_news と news_symbols を結合して銘柄別に記事を集約、1銘柄あたり件数と文字数の上限を設けてトリム。
    - OpenAI（gpt-4o-mini）の JSON Mode を用いたバッチ処理（最大 20 銘柄/チャンク）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフによるリトライ。
    - レスポンスバリデーション（JSON の抽出・results 配列検証・コード照合・数値検証）を行い、スコアを ±1.0 にクリップ。
    - DuckDB 互換性のため、ai_scores 書き込みは部分的な保護（対象 code のみ DELETE → INSERT）とし、executemany の空リスト回避を実装。
    - API 呼び出し部分はテスト時に差し替え可能（_call_openai_api を patch で置換）。
  - regime_detector.score_regime:
    - ETF 1321（日経225 連動 ETF）200 日移動平均乖離（ma200_ratio）とマクロニュースの LLM センチメントを合成して市場レジーム（bull/neutral/bear）を判定。
    - マクロキーワードで raw_news をフィルタ、最大記事数制限、LLM 呼び出しは JSON パースとリトライ制御を含む。
    - レジームスコアの算出式と閾値（重み: MA 70%, マクロ 30%）を実装。
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - API キー解決は引数優先、未設定時は OPENAI_API_KEY 環境変数を参照。未設定時は ValueError。
- Research モジュール（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を DuckDB で計算。
    - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を結合して PER / ROE を算出（EPS 不在時は None）。
    - 計算はすべて DuckDB 上の SQL ウィンドウ関数等を利用して効率的に実装。データ不足時は None を返す設計。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを LEAD で一括取得。
    - calc_ic: スピアマン相関（ランク相関）による IC 計算を実装（同順位は平均ランク）。
    - factor_summary: カウント/平均/標準偏差/最小/最大/中央値を算出する統計サマリー。
    - rank: 値をランクに変換（同順位は平均ランク、丸めで ties の検出精度を向上）。
  - kabusys.research.__init__ で主要関数を再エクスポート（zscore_normalize を含む）。
- Data モジュール（kabusys.data）
  - calendar_management:
    - JPX マーケットカレンダー管理関数群（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB にカレンダー情報がない場合は曜日ベース（土日を非営業日）でフォールバックする一貫したロジック。
    - calendar_update_job: J-Quants クライアント経由で差分取得し market_calendar を冪等保存（backfill と健全性チェックあり）。
    - 最大探索範囲制限やバックフィル、直近データの訂正を取り込む設計。
  - pipeline / etl:
    - ETLResult dataclass を導入し ETL 実行結果（取得数・保存数・品質問題・エラー）を構造化して返却可能に。
    - pipeline モジュール（ETLパイプラインの設計、差分取得・保存・品質チェックのフローに対応）。
    - data.etl で ETLResult を公開再エクスポート。
  - DuckDB 互換性への配慮（executemany で空リスト不可への対応など）と、DB 書き込み操作の冪等性確保。
- ロギング・テスト性・堅牢性の向上
  - API コールでの例外制御（RateLimitError, APIConnectionError, APITimeoutError, APIError 等）や JSON パースエラーに対するフォールバック動作を統一。
  - LLM 呼び出し関数はモジュール単位で private に分離し、テストで容易にモック可能（patch 指定箇所を明示）。
  - ルックアヘッドバイアス防止のため datetime.today()/date.today() を直接参照しない方針を各所で採用（target_date 引数駆動）。

Fixed
- 初回リリースのため特定の「修正」はなし（既存コード内に設計上の注意点あり。下記参照）。

Known issues / Notes
- pipeline._get_max_date の末尾でコードが途中（date.fro）で切れているように見えます。これはファイル提供時点での切断・タイポの可能性が高く、当該関数は正しい日付変換ロジック（DuckDB からの値変換）を期待します。リリース前に該当箇所の修正（正しい日付変換・戻り値）を要確認。
- DuckDB バインドと executemany の挙動はバージョン依存の問題があるため、空パラメータ回避等のワークアラウンドを実装済み。DuckDB の将来バージョンで不要になる可能性あり。
- OpenAI SDK のバージョン差（例: APIError の属性名）を吸収するため getattr を利用しているが、SDK の大幅な変更時は追加対応が必要。
- News/Regime の LLM スコアは外部 API に依存するため、API 利用上限や料金に注意。API キーは api_key 引数で注入可能（テスト容易化）。

Security
- 本リリースでセキュリティ修正は特に無し。ただし API キーやトークンは環境変数で管理することを想定（Settings で取得）。.env ファイルをプロダクションで使う場合の管理に注意。

Acknowledgements / Other
- OpenAI の JSON Mode（response_format）を使用して厳密な JSON レスポンスを期待する実装となっているため、実運用ではモデルの応答挙動や rate-limit を考慮した運用設計が必要です。
- 各モジュールはユニットテストが差し替え可能な設計（_call_openai_api の patch 等）になっており、モック注入で API 呼び出しを回避したテストが可能です。

----- 

注: 上記は提供されたソースコード内容から推測して作成した CHANGELOG です。実際のリリースノートとして使用する場合は、実装差分やコミット履歴に基づいた最終確認を行ってください。