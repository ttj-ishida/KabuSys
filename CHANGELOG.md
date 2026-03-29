CHANGELOG
=========

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog の様式に準拠しています。

Unreleased
----------

### Added
- なし（初回リリースに向けた安定化・小改善等は次バージョンで）

[0.1.0] - 2026-03-29
--------------------

初回公開リリース。以下の主要機能・モジュールを実装・追加しました。

### Added
- パッケージ基礎
  - kabusys パッケージ初期化（src/kabusys/__init__.py）。バージョン "0.1.0" を設定し、公開 API として data, strategy, execution, monitoring をエクスポート。

- 環境設定/ローダ
  - 環境変数および .env ファイルを自動読み込みする設定モジュールを実装（src/kabusys/config.py）。
    - プロジェクトルートの探索は __file__ から上位ディレクトリを探索し、.git または pyproject.toml を検出して決定（CWD 非依存）。
    - .env と .env.local を優先順位付きで読み込み。OS 環境変数を保護（.env.local は上書き可、ただし既存の OS 環境変数は保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - .env のパースは export プレフィックス、シングル/ダブルクォート、エスケープ、行末コメント（スペース前の #）など多様な形式に対応。
    - Settings クラスを提供し、J-Quants / kabu / Slack / DB パス等の設定プロパティと入力検証（KABUSYS_ENV, LOG_LEVEL の許容値）を実装。
    - デフォルトの DB パス（DuckDB/SQLite）を設定。

- データレイヤ（Data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar を用いた営業日の判定ロジックを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar データがない場合は曜日ベース（土日非営業日）でフォールバック。
    - 夜間バッチ更新ジョブ calendar_update_job を実装（J-Quants クライアント経由で差分取得、バックフィル、健全性チェック、冪等保存）。
    - 最大探索範囲・先読み・バックフィル・健全性制約など安全策を実装。
  - ETL パイプライン基盤（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラス（ETL の実行結果を構造化して返す）を実装し re-export。
    - 差分取得、最終日チェック、バックフィル、品質チェック（quality モジュールと連携）を想定した設計。
    - DuckDB 周りのユーティリティ _table_exists, _get_max_date 等を実装。

- 研究用（Research）モジュール（src/kabusys/research/*）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン）、200 日移動平均乖離、ATR（20 日）、流動性指標（20 日平均売買代金・出来高比率）などを DuckDB SQL ベースで計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - 設計：prices_daily / raw_financials のみ参照し、本番発注 API へは一切アクセスしない。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターンの計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク変換ユーティリティ（rank）、ファクター統計サマリ（factor_summary）を実装。
    - 外部依存を避け、標準ライブラリのみで実装。欠損・データ不足時の扱いを明確化。

- AI（自然言語処理）モジュール（src/kabusys/ai/*）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのセンチメント（-1.0〜1.0）を算出し ai_scores テーブルに書き込む処理を実装（score_news）。
    - タイムウィンドウ定義（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）を正確に計算する calc_news_window を提供。
    - バッチ処理（最大 20 銘柄/コール）、テキストトリム（記事数上限・文字数上限）、レスポンス検証、スコアのクリッピング（±1.0）、部分書き換えによる冪等保存を実装。
    - API 呼び出しは429/ネットワーク/タイムアウト/5xx に対して指数バックオフでリトライ。致命的でない失敗はスキップして継続（フェイルセーフ）。
    - テスト容易性のため _call_openai_api をパッチ差し替え可能に設計。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225 連動）の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定（score_regime）。
    - ma200_ratio 計算、マクロキーワードによる raw_news フィルタ、OpenAI 呼び出し（gpt-4o-mini）による macro_sentiment の評価を実装。API 失敗時は macro_sentiment=0.0 としてフォールバック。
    - レジームスコア合成としきい値判定（閾値の定義あり）、結果は market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）で保存。
    - LLM 呼び出しの再試行/エラーハンドリング、JSON パース失敗時のフォールバックを実装。
    - テスト用に _call_openai_api の差し替えを想定。

### Changed
- なし（新規実装群のため、変更履歴は初回追加に集約）

### Fixed
- なし

### Security
- なし特記事項。ただし以下の安全策を実装:
  - 環境変数の保護（OS 環境変数が .env によって上書きされない仕組み）
  - API キー未設定時に明確な ValueError を送出
  - DB トランザクション失敗時は ROLLBACK を試みる実装（失敗ログを含む）

### Notes / 設計方針（重要な実装上の判断）
- ルックアヘッドバイアス対策: いずれのアルゴリズムも内部で datetime.today()/date.today() を直接参照せず、呼び出し側が target_date を与える方式で実装。
- DuckDB を第一選択の内部 DB として想定。executemany に空リストを渡せないバージョンへの互換性考慮あり。
- 外部依存を最小化（AI モジュールは OpenAI SDK を利用するが、研究/データ処理は標準ライブラリ + DuckDB SQL で完結）。
- 冪等性を重視：DB 書き込みは既存行の削除 → 挿入、または ON CONFLICT 想定の save_* を使うことで再実行可能性を確保。

今後の予定（含む可能性が高い改善点）
- monitoring モジュールの実装（パッケージ公開時点では __all__ に含まれるが実体は別途整備予定）
- より詳細なユニットテストとエンドツーエンドの統合テストの追加
- J-Quants / kabu ステーション クライアントの接続例・エラーリカバリの拡充
- ドキュメント（API リファレンス、運用手順、環境変数一覧）の整備

署名
----
- 作成日: 2026-03-29
- この CHANGELOG はコードベースの実装内容から推測して記載しています。実際のリリースノートはバージョン管理履歴・リリース担当の判断を優先してください。