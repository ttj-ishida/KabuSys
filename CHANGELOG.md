# Changelog

すべての注記は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠します。  
このプロジェクトはセマンティックバージョニングを採用します。

現在のバージョン: 0.1.0

## [Unreleased]
（今後の変更予定や WIP の記載用。現時点では未指定）

---

## [0.1.0] - 2026-03-29

初回リリース。日本株自動売買プラットフォームの基礎機能をまとめて実装しました。以下の主要機能と設計方針を含みます。

### Added
- パッケージ基盤
  - パッケージ初期化（kabusys.__init__）とバージョン定義（__version__ = "0.1.0"）。
  - 公開モジュール群のエクスポート設定（data, strategy, execution, monitoring）。

- 環境設定 / 設定管理（kabusys.config）
  - .env / .env.local 自動読み込み（プロジェクトルートを .git / pyproject.toml から判定）。
  - 読み込み制御: KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - .env パーサーの実装:
    - export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント等に対応。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 環境（development/paper_trading/live）などのプロパティ取得とバリデーションを実装。
  - 環境変数の上書きポリシー（OS 環境変数保護）対応。

- データプラットフォーム（kabusys.data）
  - ETL パイプライン基盤（kabusys.data.pipeline）:
    - 差分取得・バックフィル・品質チェックの設計方針を具現化。
    - ETLResult データクラス（実行結果記録、品質問題・エラー収集、辞書変換ユーティリティ）。
    - DuckDB 互換性を考慮したテーブル存在チェック / max date 取得などのユーティリティ。
  - マーケットカレンダー管理（kabusys.data.calendar_management）:
    - market_calendar テーブルを用いた営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB データ優先、未登録日は曜日ベースのフォールバック。
    - calendar_update_job による J-Quants からの差分取得・バックフィル・健全性チェック（将来日付の異常検出）と冪等保存の呼び出し。
    - 最大探索範囲制限（_MAX_SEARCH_DAYS）で無限ループ防止。

- 研究（Research）モジュール（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を計算。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials に基づく PER, ROE の算出（最新財務レコードを参照）。
    - 設計上、prices_daily / raw_financials のみ参照しルックアヘッドを防止。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21] 営業日）の将来リターンを一度のクエリで計算。
    - calc_ic: スピアマンのランク相関による IC（Information Coefficient）計算。
    - rank: 同順位は平均ランクを返すランク変換ユーティリティ（丸め処理で ties の検出漏れ防止）。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を計算。
  - kabusys.research から便利関数を再エクスポート。

- AI（自然言語処理）モジュール（kabusys.ai）
  - news_nlp:
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄別センチメントスコア（-1.0〜1.0）を算出。
    - ニュースウィンドウは JST ベースで前日 15:00 ～ 当日 08:30（内部は UTC naive datetime で扱う）。calc_news_window を提供。
    - バッチ処理（最大20銘柄 / チャンク）、1銘柄あたり記事数と文字数の上限を実装（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - API 呼び出しのリトライ（429・ネットワーク・5xx・タイムアウト等）と指数バックオフ、レスポンスの堅牢なバリデーション（JSON 抽出、results 構造チェック、コード照合、数値チェック）。
    - DuckDB executemany の制約対応（空パラメータ回避のガード）。
    - API 失敗時は該当チャンクをスキップして処理継続（フェイルセーフ）。
  - regime_detector:
    - ETF 1321（Nikkei 225 連動型 ETF）の 200 日移動平均乖離（重み 70%）と、news_nlp により取得または LLM 評価されたマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出。
    - LLM 呼び出しは独自実装（モジュール結合低減のため news_nlp と共有しない）。
    - API 呼び出しのリトライ、失敗時は macro_sentiment=0.0 にフォールバック。
    - 計算結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - ルックアヘッドバイアス防止: target_date 未満のみを参照、datetime.today() を参照しない。
  - テスト容易性: 各モジュールの OpenAI 呼び出しポイントは差し替え可能（unittest.mock.patch を想定）。

### Changed
- （初回リリースのため、互換性や挙動のドキュメント化を明確化）
  - DuckDB のバージョン差異（executemany の空リスト制約等）を考慮した実装と注記を追加。
  - ルックアヘッドバイアスに対する設計原則を各モジュールで徹底（日時参照やクエリの排他条件等）。

### Fixed / Robustness
- 環境変数パーサーの強化:
  - クォート内のバックスラッシュエスケープ処理、クォート外のインラインコメント判定の改良、export プレフィックス対応で .env パースの堅牢性を向上。
- OpenAI API ハンドリング:
  - JSON Mode での余計な前後テキスト混入に備えた JSON 抽出ロジックを実装。
  - APIError の status_code 存在有無に依存しない安全なリトライ判定。
- データ不足時の安全処理:
  - ma200 / ATR 等のウィンドウが不十分な場合は None や中立値（1.0 / 0.0）を返し、処理継続かつログ出力する。
- トランザクションとエラーハンドリング:
  - DB 書き込み時の例外で ROLLBACK を試行し、それでも失敗した場合は警告ログを出す実装。

### Other / Notes
- 多くの箇所でログ出力（info/debug/warning）を追加し、運用時の可観測性を確保。
- OpenAI モデルは gpt-4o-mini を前提としているが、API キーは引数注入または環境変数 OPENAI_API_KEY から取得可能。
- セキュリティに関しては環境変数の扱いと OS 環境変数保護（protected keys）の設計を導入。

---

今後の予定（参考）
- strategy / execution / monitoring の具現化（発注ロジック、実口座接続、モニタリング通知）。
- 単体テスト・統合テストの整備（CI パイプライン）。
- パフォーマンス改善（大規模データ時の DuckDB クエリ最適化、並列化など）。
- 追加 AI モデルやハイパーパラメタの運用用設定化。

---

著記: 上記はソースコードの実装から推測した変更履歴です。リリースノートや実運用上の正確な差分はバージョン管理履歴（git log）やリリース手順に基づいて補完してください。