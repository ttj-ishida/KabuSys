# CHANGELOG

すべての注目すべき変更履歴をここに記録します。  
このファイルは Keep a Changelog のフォーマットに準拠しています。  
バージョン番号は semver を想定しています。

## [0.1.0] - 2026-03-26

初回公開リリース。以下の主要機能群・モジュールを追加しました。

### Added
- パッケージの公開情報
  - pakage メタ: kabusys/__init__.py に __version__ = "0.1.0"、主要サブパッケージを __all__ で公開（data, strategy, execution, monitoring）。

- 環境設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定をロードするユーティリティを実装。
  - プロジェクトルート自動検出（.git または pyproject.toml を基準）により、CWD に依存しない .env 自動読み込みを実現。
  - .env のパースロジックを強化（export プレフィックス、クォート内エスケープ、インラインコメント判定など）。
  - 自動ロードを環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを提供：J-Quants・kabuステーション・Slack・DBパス・実行環境・ログレベル等のプロパティ（必須項目は未設定時に ValueError を送出）。
  - デフォルト値：KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH、KABUSYS_ENV=development、LOG_LEVEL=INFO など。

- データプラットフォーム（kabusys.data）
  - calendar_management:
    - JPX マーケットカレンダー管理。market_calendar テーブルの存在チェック、営業日判定（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）を実装。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする挙動を採用し、DBがまばらな場合でも一貫性を担保。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新。バックフィルと健全性チェックを実装。
  - pipeline / etl:
    - ETLResult データクラスを実装して ETL の実行結果（取得数・保存数・品質問題・エラー）を表現できるようにした。
    - ETL の差分更新、バックフィル方針や品質チェック設計を仕様に明記（実装は jquants_client / quality と連携する想定）。
  - etl 模組：kabusys.data.etl は pipeline.ETLResult を再エクスポート。

- 研究用（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を DuckDB の prices_daily から計算。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務を取得して PER / ROE を計算（EPS 不在またはゼロ時は None）。
    - 各関数はデータ不足時に None を返す設計、DuckDB を用いた SQL + Python 実装、外部 API へはアクセスしない。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（例: 1,5,21 営業日）に対する将来リターンを計算。horizons の検証を実装。
    - calc_ic: Spearman ランク相関（Information Coefficient）を実装。データ不足（有効レコード < 3）時は None を返す。
    - rank: 同順位は平均ランクにするランク関数を実装（浮動小数の丸めで ties を安定化）。
    - factor_summary: カウント・平均・標準偏差・最小・最大・中央値を計算する統計サマリー機能。
  - 研究モジュールは pandas 等の外部ライブラリに依存せず標準ライブラリ + duckdb で実装。

- AI / ニュース NLP（kabusys.ai）
  - news_nlp:
    - raw_news と news_symbols を集約し、銘柄ごとの記事群を LLM（gpt-4o-mini）へバッチ送信してセンチメント（-1.0〜1.0）を算出。
    - チャンク処理（最大 20 銘柄/コール）、1銘柄あたりの記事数・文字数上限（トークン肥大化対策）を実装。
    - OpenAI JSON mode を用いたレスポンス処理と堅牢なバリデーション（JSON 抽出、results 配列、code/score 検証、スコアのクリップ）。
    - リトライ戦略（429 / ネットワーク断 / タイムアウト / 5xx を指数バックオフでリトライ）、API失敗時はスキップして継続（フェイルセーフ）。
    - ai_scores テーブルへの冪等書き込み（該当コードのみ DELETE → INSERT）により部分失敗時の既存データ保護を実現。
  - regime_detector:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定。
    - マクロニュースは news_nlp のウィンドウ計算を利用して抽出。OpenAI 呼び出しは独立実装でモジュール結合を防止。
    - API 失敗時は macro_sentiment = 0.0 へフォールバックし処理継続（フェイルセーフ）。
    - レジーム計算後は market_regime テーブルへ冪等的に（BEGIN/DELETE/INSERT/COMMIT）書き込み。DB 書き込み失敗時は適切に ROLLBACK を試行して例外を伝播。

- OpenAI クライアント呼び出し箇所について
  - news_nlp と regime_detector はそれぞれ独自の _call_openai_api を持ち、テスト時に差し替え可能（unittest.mock.patch によりモック化しやすい設計）。

### Changed
- （初回リリースのためなし）

### Fixed
- （初回リリースのためなし）

### Design / Implementation Notes（設計上の重要な判定や安全策）
- ルックアヘッドバイアス回避: 日付判定ロジック（score_news / score_regime 等）は datetime.today() / date.today() を内部参照せず、呼び出し元から target_date を受け取る設計。
- DuckDB 互換性: executemany に空リストを渡せないケース（DuckDB 0.10）を考慮して条件分岐を実装。
- 安全な DB 書き込み: 複数箇所で BEGIN/COMMIT/ROLLBACK を明示的に扱い、ROLLBACK 失敗時は警告ログを出力。
- フェイルセーフ: LLM/外部API の失敗は致命的にせず、デフォルト値で継続する方針（例: macro_sentiment=0.0、スコア未取得はスキップ）。
- 外部依存の最小化: 研究モジュールは外部依存を避け、標準ライブラリだけで計算可能に設計。

---

今後のリリースでは以下のような追加・改善を想定しています（検討中）:
- strategy / execution / monitoring サブパッケージの具体的実装と発注フローの統合
- jquants_client の詳細実装とテストカバレッジ拡充
- AI モデル切り替えやローカル実行時の代替パスの提供
- メトリクス収集・監視機能の強化

変更や誤りの報告、改善提案は歓迎します。