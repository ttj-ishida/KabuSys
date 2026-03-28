CHANGELOG
=========

すべての重要な変更点をこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠します。

[Unreleased]
------------

- （現時点では未リリースの変更はありません）

[0.1.0] - 2026-03-28
-------------------

Added
- 初回リリース: kabusys パッケージ v0.1.0 を追加。
  - パッケージ公開情報:
    - __version__ = "0.1.0"
    - パッケージ公開 API: data, strategy, execution, monitoring

- 環境設定/読み込み (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルート判定は .git または pyproject.toml を基準に行い、cwd に依存しない実装。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - .env パーサー: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行コメント処理（インラインコメントの取り扱いを適切に処理）に対応。
  - _load_env_file による override/protected（OS 環境変数保護）ロジックを実装。
  - Settings クラスを提供（環境変数の取得・バリデーション）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL (デフォルト値あり)
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH / SQLITE_PATH の Path 型返却（expanduser 対応）
    - KABUSYS_ENV の値検証 (development, paper_trading, live)
    - LOG_LEVEL の値検証 (DEBUG/INFO/WARNING/ERROR/CRITICAL)
    - ヘルパー: is_live, is_paper, is_dev

- データ基盤 (kabusys.data)
  - calendar_management:
    - JPX カレンダー管理（market_calendar テーブル）と営業日判定ヘルパー群を実装:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB の値を優先し、未登録日は曜日ベースのフォールバックを利用（曜日ベースでの一貫性を確保）
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新（バックフィル・健全性チェックあり）
    - 最大探索日数やバックフィル日数等の定数で安全性を確保
  - pipeline / ETL:
    - ETLResult データクラスを公開（data.etl で再エクスポート）
      - ETL の各種集計フィールド、品質チェック結果、エラーリストを保持
      - has_errors / has_quality_errors / to_dict を提供
    - ETL パイプライン用ユーティリティ: テーブル存在チェック、最大日付取得、差分更新・バックフィル設計方針

- 研究用分析モジュール (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を計算
      - データ不足時の取り扱い（不足だと None）や営業日スキャンバッファを考慮
    - calc_volatility: 20日 ATR、ATR 比率、20日平均売買代金、出来高比率を計算
      - true_range の NULL 伝播を正確に扱う実装
    - calc_value: raw_financials から最新財務を取得し PER, ROE を計算
  - feature_exploration:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得
      - horizons のバリデーション（正の整数かつ <= 252）
    - calc_ic: ファクターと将来リターン間のスピアマンランク相関（IC）を計算
      - 有効レコード数が 3 未満の場合は None
    - rank: 同順位は平均ランクで扱うランク変換（丸め処理で ties の誤差を抑制）
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリ

- AI / NLP (kabusys.ai)
  - news_nlp:
    - score_news: raw_news / news_symbols を集約して OpenAI (gpt-4o-mini) にバッチ送信し銘柄ごとの ai_score を ai_scores テーブルへ書き込む。
    - タイムウィンドウは JST ベース（前日 15:00 ～ 当日 08:30）を UTC に変換して比較。
    - バッチサイズ、記事文字数上限、記事数上限を設定してトークン肥大化に対処。
    - JSON Mode のレスポンス検証（復元処理を含む）、LLM レスポンスのバリデーションと ±1.0 クリップ。
    - リトライ/バックオフ（429、ネットワーク、タイムアウト、5xx）とフェイルセーフ（失敗時はスキップして続行）。
    - DuckDB executemany の互換性を考慮した空リストチェックと冪等 DELETE → INSERT 処理。
  - regime_detector:
    - score_regime: ETF 1321 の 200 日 MA 乖離 (重み 70%) とマクロ経済ニュースの LLM センチメント (重み 30%) を合成して日次で市場レジーム（bull/neutral/bear）を判定し market_regime に書き込む。
    - マクロニュース抽出（定義済みキーワード群）、OpenAI 呼び出し、レスポンス JSON パース、重み合成、閾値によるラベル付け。
    - API エラー時は macro_sentiment=0.0 のフェイルセーフ。DB は BEGIN/DELETE/INSERT/COMMIT の冪等書き込み、失敗時は ROLLBACK。

- パッケージ初期エクスポート:
  - kabusys.ai.__all__ に score_news
  - kabusys.research.__all__ に主要分析関数と zscore_normalize を追加
  - kabusys.data.etl は ETLResult を再エクスポート

Security / Safety / Design notes
- 全ての AI スコア・レジーム判定はルックアヘッドバイアスを避ける設計（datetime.today()/date.today() を直接参照しない、DB クエリで date < target_date 等の排他条件を利用）。
- OpenAI 呼び出しはタイムアウト・リトライ・ステータスコード判定を含む堅牢な実装。API 失敗はフェイルセーフで 0.0 またはスキップにフォールバックし、致命的な例外を抑制。
- DuckDB のバージョン差異に対する互換性考慮（executemany の空リスト問題、list 型バインドの回避など）。
- 環境変数自動ロード処理はプロジェクトルート検出失敗時にスキップし、CI/テスト用に KABUSYS_DISABLE_AUTO_ENV_LOAD で抑制可能。

Fixed
- 初期リリースにおける既知の堅牢性対策:
  - DB トランザクション実行中の例外発生時に ROLLBACK を試みる（ROLLBACK 自体が失敗した場合は警告ログを出力して上位へ再送出）。
  - OpenAI レスポンスのパース失敗や予期しない JSON 形式に対する復元ロジックを追加（外側の {} を抽出するなど）。

Compatibility
- 依存: duckdb, openai (OpenAI Python SDK)
- OpenAI モデル: gpt-4o-mini を利用する設計
- DuckDB の SQL 機能（ウィンドウ関数、executemany 等）に依存

Notes
- 必須の環境変数（例）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（AI 機能を使う場合）
- ドキュメントや設計方針は各モジュールの docstring に記載

(今後)
- 既知の拡張候補: PBR・配当利回りの追加、戦略モジュールの実装、monitoring / execution 周りの詳細な実装とテスト強化。