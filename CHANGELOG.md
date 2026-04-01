CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  
安定版リリースはセマンティックバージョニングを使用します。

Unreleased
----------
- （現時点で未リリースの変更はありません）

[0.1.0] - 2026-04-01
--------------------

Added
- 初回公開: kabusys パッケージ v0.1.0 を追加。
  - パッケージ構成:
    - kabusys.config: 環境変数／設定管理
      - プロジェクトルートを .git / pyproject.toml から検出して .env/.env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD により抑止可能）。
      - .env パーサは export 形式・クォート・エスケープ・インラインコメント等に対応。
      - 既存 OS 環境変数を保護するための上書き制御（protected set）を実装。
      - Settings クラスで J-Quants や kabu ステーション、Slack、データベースパス、監視閾値、実行環境（development/paper_trading/live）やログレベルをプロパティとして取得・バリデーション。
    - kabusys.ai
      - news_nlp: ニュースに対する NLP スコアリング機能
        - raw_news / news_symbols を集約して銘柄ごとに記事をまとめ、OpenAI（gpt-4o-mini、JSON Mode）にバッチ送信してセンチメントを取得。
        - バッチサイズ・文字数上限・記事数上限によるトークン制御を実装。
        - 429 / ネットワーク断 / タイムアウト / 5xx に対するエクスポネンシャルバックオフ・リトライ。
        - レスポンスの厳密なバリデーション（JSON 抽出、results 配列、code/score の整合性）と ±1.0 のクリップ。
        - スコア取得後に ai_scores テーブルへ冪等的に（DELETE → INSERT）保存。部分失敗時に既存スコアを保護する実装。
        - calc_news_window ユーティリティで JST のニュースウィンドウを UTC 換算して扱う（ルックアヘッド防止）。
      - regime_detector: 市場レジーム判定
        - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロセンチメント（重み30%）を合成して日次で 'bull' / 'neutral' / 'bear' を判定。
        - prices_daily と raw_news を参照して ma200_ratio とマクロ記事集合を取得し、OpenAI により macro_sentiment を算出（記事無し時は LLM 呼出しをスキップ、macro_sentiment=0.0）。
        - API 認証は api_key 引数または環境変数 OPENAI_API_KEY を利用。
        - 冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）で market_regime テーブルを更新。
        - API 失敗などに対するフェイルセーフ（マクロスコアを 0 にフォールバック、例外を上位に伝播しない制御）。
    - kabusys.research
      - factor_research: モメンタム / ボラティリティ / バリューの定量ファクター算出
        - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None）。
        - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率等。
        - calc_value: raw_financials から最新財務を取得して PER / ROE を算出。
        - 全て DuckDB 上の SQL（ウィンドウ関数）で実装し、外部 API へはアクセスしない設計。
      - feature_exploration: 将来リターン / IC / 統計サマリー
        - calc_forward_returns: 指定ホライズン先のリターンを LEAD を用いて一括算出。
        - calc_ic: スピアマンのランク相関（IC）を実装（有効レコードが 3 未満なら None）。
        - rank / factor_summary: 同順位は平均ランク、カラム毎の count/mean/std/min/max/median を計算。
        - 外部依存（pandas 等）を使わず標準ライブラリで実装。
      - research パッケージから zscore_normalize を再エクスポート。
    - kabusys.data
      - calendar_management: 市場カレンダー管理
        - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を実装。
        - market_calendar テーブルを優先し、未登録日は曜日ベースでフォールバック（週末は非営業日）。
        - calendar_update_job により J-Quants から差分取得・バックフィル・保存を行う（健全性チェックを実装）。
      - pipeline / etl: ETL 基盤
        - ETLResult dataclass を公開（target_date, fetched/saved counts, quality_issues, errors 等）。
        - pipeline モジュールの設計により差分取得・保存（idempotent）・品質チェックを行う方針を反映。
        - ETL の backfill と品質チェックは非 Fail-Fast の設計（問題を収集して呼び出し元が判断）。
      - DuckDB 特有の注意点（executemany に空リストを渡せない等）への対応実装。
    - パッケージAPI整理
      - パッケージ __all__ に data / strategy / execution / monitoring を含めた公開方針（monitoring 等の実装は別ファイルで提供想定）。

Fixed
- 初回リリースのため該当なし。

Changed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

注記（既知の制限・運用上の注意）
- OpenAI API
  - news_nlp / regime_detector は gpt-4o-mini の JSON Mode を利用する想定。API キー（OPENAI_API_KEY）または関数引数での注入が必須。
  - API エラー時は安全側でスコアを 0 にフォールバックする実装のため、ネットワーク障害時でも処理は継続しますが、センチメント寄与が無くなります。
- 時刻・タイムゾーン
  - news のウィンドウ計算は JST を基準にして UTC naive datetime を生成します。DB 側の raw_news.datetime は UTC で保存されている前提で動作します。
- DuckDB 互換性
  - DuckDB バージョン差異（特に executemany の空リストバインド）へのワークアラウンドを実装していますが、環境差異による動作確認を推奨します。
- 未実装 / 要確認
  - 一部コード断片（pipeline._get_max_date の末尾など）が途中で切れている箇所が見られます（開発中の断片と思われます）。該当箇所は実装補完・単体テストが必要です。
  - パッケージ __all__ に含まれる monitoring 等のモジュール実体が本差分内で確認できないため、別途実装または外部提供が必要です。
- テスト性
  - OpenAI 呼び出し箇所は内部の _call_openai_api を unittest.mock.patch で差し替えることを想定しています。ユニットテストの容易化を考慮した設計です。

今後の予定（例）
- pipeline の完全実装と ETL ワークフローのユニット/統合テスト整備。
- monitoring モジュールの実装（PID ファイル監視・リソース閾値超過アラート等）。
- CI/CD と静的解析（型チェック、lint）を導入。
- ドキュメント（README / API リファレンス / デプロイ手順）の充実。

----- 
この CHANGELOG はソースコードから推測して作成しています。実際のコミット履歴や開発ノートがある場合はそちらを優先のうえ、必要に応じて差分を反映してください。