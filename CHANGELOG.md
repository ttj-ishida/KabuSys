CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従います。  
安定版リリースと互換性ポリシーはセマンティックバージョニングに従います。

[0.1.0] - 2026-04-01
--------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージメタ情報
    - src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。
- 環境変数 / 設定管理
  - src/kabusys/config.py
    - .env 自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml で検出）。
    - .env/.env.local の読み込み順序を実装（OS 環境変数 > .env.local > .env）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート。
    - .env パース機能を強化:
      - コメント行、先頭に export を付けた形式のサポート。
      - シングル/ダブルクォート内のバックスラッシュエスケープ処理。
      - クォート無し値のインラインコメントの取り扱い（直前が空白/タブの場合に認識）。
    - 環境変数取得ユーティリティ _require()（未設定時は ValueError）。
    - Settings クラスを公開（J-Quants / kabu API / Slack / DB パス / 監視閾値 / 環境判定等のプロパティを提供）。  
      - KABUSYS_ENV と LOG_LEVEL の値検証を実装（無効値は ValueError）。
      - デフォルト値や Path の展開（expanduser）を備える。
- AI（ニュース NLP・市場レジーム判定）
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を結合して銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄別センチメントを算出。
    - タイムウィンドウの計算（前日 15:00 JST ～ 当日 08:30 JST 相当の UTC 範囲）を calc_news_window() で提供。
    - バッチ処理（最大 20 銘柄 / チャンク）、記事数・文字数のトリム、レスポンス検証、スコアの ±1.0 クリップを実装。
    - エラー耐性: 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライし、上限到達時は当該チャンクをスキップ（フェイルセーフ）。
    - DuckDB の互換性考慮（executemany に空リストを渡さない等）。
    - テストしやすさのため _call_openai_api をパッチ置換可能に設計。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動型）に対する 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を統合して日次の市場レジーム（bull/neutral/bear）を算出する score_regime() を実装。
    - prices_daily からの MA200 計算（ルックアヘッド防止のため target_date 未満のみ使用）と、raw_news からのマクロキーワード抽出ロジックを提供。
    - OpenAI 呼び出しは専用実装で分離し、API エラー時は macro_sentiment=0.0 として継続（フェイルセーフ）。
    - 計算結果は market_regime テーブルへ冪等（BEGIN / DELETE / INSERT / COMMIT）で保存。
    - リトライ・エラー処理、ログ出力を実装。
- Research（ファクター計算・特徴量探索）
  - src/kabusys/research/factor_research.py
    - モメンタム (1M/3M/6M)、200 日 MA 乖離、ATR（20 日）、流動性（20 日平均売買代金・出来高比率）、バリュー指標（PER、ROE）の計算関数を提供（calc_momentum / calc_volatility / calc_value）。
    - DuckDB のウィンドウ関数を活用した SQL ベース実装。データ不足時は None を返す挙動。
    - 設計上、本モジュールは prices_daily/raw_financials のみ参照し、注文や外部 API へはアクセスしない。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算 calc_forward_returns（任意ホライズン対応、horizons 検証）を実装。
    - Spearman ランク相関（IC）を計算する calc_ic（欠損・同値・レコード不足時の取り扱いを含む）。
    - ランク変換ユーティリティ rank（同順位は平均ランク、丸めで ties 判定の安定化）。
    - factor_summary による count/mean/std/min/max/median の統計サマリー機能。
    - pandas 等に依存しない、標準ライブラリ + DuckDB ベースの実装。
  - research パッケージ公開: 主な関数を __all__ で再公開。
- Data（ETL / カレンダー管理 / パイプライン）
  - src/kabusys/data/calendar_management.py
    - JPX マーケットカレンダーの管理機能を実装（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - market_calendar が未取得の場合は曜日ベースでフォールバック（土日非営業扱い）。
    - カレンダー差分取得ジョブ calendar_update_job を実装（J-Quants から差分取得・バックフィル・健全性チェック・保存呼び出し）。
    - DB 値優先・未登録日は曜日フォールバックという一貫した挙動を保持。
    - 検索上限（_MAX_SEARCH_DAYS）により無限ループを防止。
  - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py
    - ETL パイプラインの高水準インターフェースと ETLResult データクラスを実装。
    - 差分取得・保存（jquants_client 経由の idempotent な保存）・品質チェック（quality モジュール利用）のフローを想定。
    - ETLResult は品質問題やエラーの集約、has_errors / has_quality_errors / to_dict のユーティリティを提供。
    - DuckDB テーブル存在チェックや最大日付取得等のユーティリティを実装。
    - ETL の設計は backfill_days を考慮した差分再取得、品質チェックは Fail-Fast とせず結果を集めて上位で判断する方針。
  - データモジュールは jquants_client（外部クライアント）との統合ポイントを想定（fetch/save 系関数呼び出し）。
- パッケージ公開
  - data パッケージの ETLResult を kabusys.data.etl で再公開。

Changed
- 初回リリースのため該当なし。

Deprecated
- 該当なし。

Removed
- 該当なし。

Fixed
- 初回リリースのため該当なし（ただし各モジュールでフォールバック・フェイルセーフや DuckDB 互換性の注意点を実装）。

Security
- OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY で指定する必要がある（未設定時は ValueError を送出）。  
- .env 自動ロードはデフォルトで有効だが、テスト等で無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD を提供。

Notes / 注意事項
- ルックアヘッドバイアス対策:
  - 多くの日次処理（news_nlp.score_news / regime_detector.score_regime / research の計算等）は内部で datetime.today() / date.today() を参照せず、明示的に渡された target_date の前後データのみを参照する設計になっています。運用時は必ず target_date を明示してください。
- OpenAI 呼び出し:
  - gpt-4o-mini の JSON mode を利用する想定。テストでは _call_openai_api をモックすることで外部依存を切り離せます。
- DuckDB 注意:
  - DuckDB のバージョン差異に対する互換性注記（例: executemany に空リストを渡せない制約）を考慮した実装があります。
- トランザクション管理:
  - market_regime / ai_scores 等の書込みは BEGIN/DELETE/INSERT/COMMIT の冪等なパターンを採用。例外発生時は ROLLBACK を試行し、失敗ログを出力します。
- ログ出力:
  - 各処理は詳細な情報/警告/例外ログを出力します。運用時は LOG_LEVEL とログ集約を適切に設定してください。

今後の計画（例）
- strategy / execution / monitoring モジュールの追加実装（発注・ポートフォリオ管理・実行監視）。
- モデル・ファインチューニングや LLM 呼び出しの最適化（プロンプト改善、アンサンブル等）。
- 品質チェック (quality) と監視アラートの拡充。

----------