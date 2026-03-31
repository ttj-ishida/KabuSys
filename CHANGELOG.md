Keep a Changelog 準拠 — kabusys

すべての重要な変更をこのファイルに記録します。フォーマットは Keep a Changelog に準拠しています。
リリース日付はリポジトリの __version__ と現行日付（2026-03-31）を基にしています。

Unreleased
----------
- （次回以降の変更をここに記載）

0.1.0 — 2026-03-31
-----------------
Added
- 初回リリース: kabusys パッケージの公開
  - パッケージ構成:
    - kabusys.config: 環境変数 / .env 管理（Settings クラス）
      - .env ファイルの自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）
      - .env のパースは export 形式、クォート、エスケープ、インラインコメントに対応
      - 読み込み順序: OS 環境変数 > .env.local > .env、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能
      - 必須変数取得ヘルパー _require と入力検証（KABUSYS_ENV, LOG_LEVEL）
      - DBファイルパス（DUCKDB_PATH / SQLITE_PATH）や監視しきい値（CPU/MEM/DISK）などのプロパティを提供
    - kabusys.ai
      - news_nlp.score_news:
        - 「前日 15:00 JST ～ 当日 08:30 JST」相当のニュースウィンドウ計算（calc_news_window）
        - raw_news と news_symbols を用いて銘柄ごとに記事を集約（記事数・文字数のトリムあり）
        - OpenAI (gpt-4o-mini) へバッチ送信（最大 20 銘柄/チャンク）し JSON Mode で受信
        - 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ
        - レスポンスの堅牢なバリデーション（JSON 抽出、results リストの検証、コード/スコア検証）
        - スコアを ±1.0 にクリップし、ai_scores テーブルへ冪等的に書き込み（DELETE → INSERT）
        - テスト容易性: _call_openai_api をモック可能
      - regime_detector.score_regime:
        - ETF 1321 の 200 日移動平均乖離（70%）とマクロニュース LLM センチメント（30%）を合成し
          market_regime テーブルへ日次で書き込み（ラベル: bull/neutral/bear）
        - マクロ記事抽出はマクロキーワードリストを用いる
        - API 呼び出し失敗時は macro_sentiment=0.0 としてフェイルセーフ動作
        - 書き込みはトランザクション（BEGIN/DELETE/INSERT/COMMIT）で冪等化
        - テスト容易性: _call_openai_api をモック可能、外部モジュールとのプライベート関数共有を避ける設計
    - kabusys.research
      - factor_research: calc_momentum / calc_volatility / calc_value
        - モメンタム（1/3/6 ヶ月）、200 日 MA 乖離、ATR、平均売買代金など定量ファクターを DuckDB SQL で算出
        - データ不足時は None を返す仕様、結果は (date, code) キーの dict リストで返却
      - feature_exploration: calc_forward_returns / calc_ic / rank / factor_summary
        - 将来リターンの一括取得 (LEAD を活用)、Spearman 相当のランク相関（IC）、統計サマリー等を提供
        - 外部ライブラリに依存せず標準ライブラリのみで実装
      - kabusys.research.__init__: zscore_normalize を re-export
    - kabusys.data
      - calendar_management:
        - market_calendar を基にした営業日判定ユーティリティ群（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）
        - DB未取得時は曜日ベース（土日除外）でフォールバック
        - カレンダー更新ジョブ calendar_update_job による J-Quants からの差分取得と保存（バックフィル・健全性チェック付き）
      - pipeline / etl:
        - ETLResult データクラスで ETL 実行結果を集約（取得件数、保存件数、品質問題、エラー 等）
        - pipeline モジュールの設計方針に従った差分取得 / 保存 / 品質チェックの枠組み
        - etl モジュールは ETLResult を公開
    - public exports:
      - パッケージ __init__ で data, strategy, execution, monitoring を __all__ に設定（トップレベル公開）

Security / Requirements
- OpenAI API 連携を行う機能は OPENAI_API_KEY が必要。api_key 引数で注入可能（ValueError を送出して不足を明示）
- J-Quants / kabu API 等の外部トークン（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）は Settings 経由で必須チェック
- .env 読み込みはデフォルトで有効。自動読み込みの無効化オプションを用意（KABUSYS_DISABLE_AUTO_ENV_LOAD）

Design decisions / Notes
- ルックアヘッドバイアス回避:
  - datetime.today() / date.today() を内部ロジック（スコア計算等）で直接参照しない方針。明示的な target_date 引数を使用。
  - DB クエリで date < target_date や半開区間を利用し将来データの参照を防止。
- DuckDB を中心とする設計:
  - 大半の集計 / ファクター計算は DuckDB SQL とウィンドウ関数で実装。
  - DuckDB の executemany の制約（空リスト不可等）に配慮した実装。
- フェイルセーフ:
  - 外部 API（OpenAI / J-Quants）失敗時は基本的に処理継続（0.0 やスキップ）で安全側に倒す。
  - DB 書き込みはトランザクションで扱い、失敗時は ROLLBACK を試行し上位へ例外を伝播。
- テスト容易性:
  - OpenAI 呼び出しは内部関数を経由しており unittest.mock.patch で差し替え可能。
  - 関数は副作用を限定（明示的な conn 引数など）してユニットテスト可能に設計。

Known limitations / TODO
- 一部のファクター（PBR・配当利回り等）は未実装（calc_value の注記参照）。
- OpenAI のレスポンス形式（JSON mode）に対する緩和処理は実装しているが、LLM 出力の多様性には注意が必要。
- pipeline の具体的な ETL フロー（jq クライアントの詳細実装・品質チェックルール等）は外部モジュールに依存するため、その整備が今後の改善対象。

License
- 本 CHANGELOG はリポジトリの内容から推測して作成しています。実際のリリースノートや日付はプロジェクト管理者の記録と照合してください。