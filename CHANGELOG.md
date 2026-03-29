# Changelog

すべての重要な変更点はこのファイルに記録します。  
このリポジトリは Keep a Changelog の形式に準拠しています。  

- リリースノートはセマンティックバージョニングに従っています。  
- 日付はリリース日です。

## [Unreleased]

---

## [0.1.0] - 2026-03-29

### Added
- パッケージ初期リリース。基本的なモジュール群を追加。
  - kabusys.__init__ にパッケージ情報と __version__ = "0.1.0" を定義。
- 環境設定/ロード機能（kabusys.config）
  - .env/.env.local の自動読み込み機能を実装。
    - プロジェクトルートは .git または pyproject.toml を起点に検出（CWD 非依存）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
    - 読み込み順序: OS 環境変数 > .env.local > .env。OS環境変数は保護（上書き回避）。
  - .env パーサは以下をサポート/考慮：
    - コメント行・空行の無視、`export KEY=val` 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、
      インラインコメントの取り扱い（クォートあり/なしで異なるルール）。
  - Settings クラスでアプリ設定を提供（プロパティで遅延取得）:
    - J-Quants / kabu API / Slack トークン等の必須パラメータチェック（未設定時は ValueError）。
    - DBパス（duckdb/sqlite）のデフォルト値と expanduser 対応。
    - KABUSYS_ENV / LOG_LEVEL の検証（許容値チェック）。
    - ヘルパー: is_live / is_paper / is_dev。

- ニュースNLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を用いて銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを評価。
  - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window として実装。
  - バッチ処理（最大 _BATCH_SIZE=20 銘柄）・トークン肥大化対策（記事数上限・文字数上限）。
  - JSON mode を利用した厳格なレスポンス検証:
    - レスポンスのパース回復処理（前後余計テキストを含む場合の {} 抽出）。
    - results 配列・code/score の存在チェック、未知コード無視、スコアを ±1.0 にクリップ。
  - リトライ戦略:
    - 429・ネットワーク断・タイムアウト・5xx を対象に指数バックオフでリトライ。
    - 非リトライ対象エラーはスキップし、処理継続（フェイルセーフ）。
  - DuckDB への書き込みは冪等（DELETE → INSERT）で、部分失敗時に既存スコアを保護。
  - テスト容易性のために OpenAI 呼び出し関数をモジュール内でパッチ可能に設計。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（Nikkei 225 連動ETF）の 200 日移動平均乖離（重み 70%）と
    マクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
  - マクロキーワードによる raw_news フィルタリング、最大記事数制限、OpenAI 呼び出しの再試行・フォールバック。
  - レジームスコアの合成ロジックと閾値（_BULL_THRESHOLD/_BEAR_THRESHOLD）を実装。
  - market_regime テーブルへの冪等書き込みを実装（BEGIN/DELETE/INSERT/COMMIT, 失敗時は ROLLBACK）。
  - API 失敗時は macro_sentiment を 0.0 としてフォールバックし続行。

- データモジュール（kabusys.data）
  - カレンダー管理（calendar_management）:
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を実装。
    - market_calendar が未取得時は曜日ベースのフォールバック（土日を非営業日扱い）。
    - カレンダー関連の夜間バッチ calendar_update_job（J-Quants から差分取得・バックフィル・健全性チェック）。
  - ETL パイプライン（pipeline）:
    - 差分取得・保存・品質チェックを行う方針の実装骨子。
    - ETLResult データクラスを実装（kabusys.data.etl で再エクスポート）。
    - テーブル存在確認・最大日付取得等のユーティリティを実装。
    - バックフィル日数やカレンダー先読み等の定数設定。
    - 品質チェック結果（quality.QualityIssue）を収集して結果に含める設計。

- リサーチモジュール（kabusys.research）
  - ファクター計算（factor_research）:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を DuckDB SQL で算出（データ不足時は None）。
    - calc_volatility: 20日 ATR（atr_20）、相対ATR（atr_pct）、20日平均売買代金、出来高比率等を算出。
    - calc_value: raw_financials と価格を組み合わせて PER・ROE を算出（最新財務レコードを銘柄ごとに取得）。
    - DuckDB 上で SQL と窓関数を活用した実装。
  - 特徴量探索（feature_exploration）:
    - calc_forward_returns: 任意ホライズンの将来リターンを一括クエリで取得（入力検証あり）。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。
    - rank: 同順位は平均ランクとするランク関数（丸め誤差対策）。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を計算。
  - 研究系関数は外部 API に依存せず、DuckDB 内の価格データのみ参照する方針。

### Changed
- n/a（初回リリースのため新規追加中心）。

### Fixed
- n/a（初回リリース）。

### Notes / Implementation & Design Decisions
- ルックアヘッドバイアス回避: news/regime/research の各処理は datetime.today() を直接参照せず、呼び出し側から target_date を受け取る設計。
- DuckDB 互換性: executemany に空リストを渡せない制約を考慮した書き込み保護（空チェック）を実装。
- テストしやすさ: OpenAI 呼び出しは内部関数として抽象化しており、unittest.mock.patch による差し替えが容易。
- フェイルセーフ: LLM/API の失敗は例外を直ちに上位へ投げるのではなく、適切にフォールバック（0.0）やスキップして全体処理を継続する方針。
- トランザクション/冪等性: DB への書き込みは可能な限り冪等に実装（DELETE → INSERT や ON CONFLICT 相当の扱い）し、部分失敗時に既存データを保護する。

---

今後のリリースでは以下を計画しています（例）:
- ドキュメントの充実（使用例、マイグレーションガイド）
- エンドツーエンドの ETL 実装とスケジューリング
- 追加のファクタ／アルファ研究関数
- 単体テスト・CI の整備

もしリリースノートに追記してほしい点（重要な設計判断や既知の制限など）があれば教えてください。