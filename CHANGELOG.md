# Changelog

すべての注目すべき変更点を記録します。  
このファイルは「Keep a Changelog」の形式に準拠します。

フォーマットの意味:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正・改善
- Removed: 削除
- Security: セキュリティ関連

## [Unreleased]

## [0.1.0] - 2026-04-03
初期公開リリース。

### Added
- パッケージ基盤
  - パッケージ名を `kabusys` として公開。バージョンは `0.1.0`。
  - public API として `data`, `strategy`, `execution`, `monitoring` を __all__ で定義。

- 環境設定 / 設定管理
  - `kabusys.config.Settings` を導入し、環境変数を型付きプロパティ経由で取得可能にした（J-Quants / kabu API / LINE / DB パス / 監視閾値 / システム環境等）。
  - プロジェクトルート自動検出機能を実装（.git または pyproject.toml を基準）。パッケージ配布後でも CWD に依存しない仕様。
  - .env 自動読み込み機能を追加（優先順位: OS 環境変数 > .env.local > .env）。テスト用途のため `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
  - .env パーサを実装。以下に対応:
    - `export KEY=val` 形式
    - シングル/ダブルクォート内のバックスラッシュエスケープ扱い
    - クォートなし行でのインラインコメント（直前が空白/タブの場合をコメントと扱う）
  - 環境値検証:
    - KABUSYS_ENV の許容値チェック（development, paper_trading, live）
    - LOG_LEVEL の許容値チェック（DEBUG, INFO, WARNING, ERROR, CRITICAL）
  - 必須環境変数未設定時に意味のある例外メッセージを返す `_require` を提供。

- データプラットフォーム（DuckDB ベース）
  - ETL のインターフェース `ETLResult` を実装（取得件数、保存件数、品質問題、エラー集計などを記録）。
  - ETL パイプライン基盤（差分取得、バックフィル、品質チェック統合、DuckDB 互換性への配慮）を実装するための基礎コードを追加。
  - `etl.py` にて `ETLResult` を再エクスポート。

- マーケットカレンダー / カレンダー管理
  - `kabusys.data.calendar_management` を追加し、JPX カレンダー取り扱いロジックを提供:
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
    - calendar_update_job: J-Quants からの差分フェッチと idempotent な保存処理（バックフィル、健全性チェックを含む）
  - DB に calendar データがない場合は曜日ベース（平日を営業日）でフォールバックする一貫したロジックを採用。
  - 最大探索日数制限・異常未来日チェック等で無限ループや誤データに対する防御を実装。

- 研究（Research）モジュール
  - ファクター計算モジュール `kabusys.research.factor_research`:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を計算
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算
    - calc_value: PER（price / EPS）、ROE を raw_financials と prices_daily から計算
    - DuckDB のウィンドウ関数を活用し、データ不足時は None を返す堅牢な実装
  - 特徴量探索モジュール `kabusys.research.feature_exploration`:
    - calc_forward_returns: 指定ホライズン先の将来リターン（複数ホライズン対応、検証あり）
    - calc_ic: スピアマン（ランク）相関で IC を計算（有効レコードが少ない場合は None）
    - rank: 同順位の平均ランクを返す実装（丸めによる tie 検出を考慮）
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー
  - これらはすべて外部 API に影響しない設計（read-only、prices_daily / raw_financials のみ参照）。

- AI / NLP 機能（OpenAI 統合）
  - `kabusys.ai.news_nlp`:
    - score_news: raw_news と news_symbols を集約し、銘柄ごとに gpt-4o-mini（JSON Mode）でセンチメント評価を実行。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を明示的に定義し、ルックアヘッドバイアスを排除。
    - 1 銘柄あたりの記事上限（件数・文字数）や _BATCH_SIZE によるバッチ送信、429/ネットワーク/5xx への指数バックオフリトライを実装。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 構造、コード検証、スコアの数値性、クリップ）を実装。
    - 書き込みは部分失敗に備え、取得できた銘柄のみを DELETE→INSERT で置換する（冪等・部分失敗耐性）。
    - テスト容易性のため OpenAI 呼び出しを置き換え可能（_call_openai_api は patch できる）。
  - `kabusys.ai.regime_detector`:
    - score_regime: ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定・保存。
    - prices_daily からの MA 計算は target_date 未満のデータのみを使用しルックアヘッドを防止。
    - マクロニュースの抽出はキーワードベース（日本・米国等の主要語）で最大記事数を制限。
    - OpenAI API 呼び出しのリトライ・フェイルセーフ（API 失敗時は macro_sentiment=0.0）を実装。
    - market_regime テーブルへの冪等な書き込み（BEGIN/DELETE/INSERT/COMMIT）を行う。

### Fixed / Improved
- .env パーサの堅牢化:
  - クォート内のバックスラッシュエスケープを正しく扱う実装により、複雑な .env 値に対応。
  - クォートなしのインラインコメント判定を改善し誤読を減少。
- OpenAI レスポンスパースの回復力強化:
  - JSON mode でも前後に余計なテキストが混入するケースに対して最外の `{...}` を抽出して復元する処理を追加。
- DuckDB 互換性考慮:
  - executemany に空リストを渡さないガードを追加（DuckDB 0.10 対応）。
  - テーブル存在確認ユーティリティを整備。

### Design / Safety notes
- ルックアヘッドバイアスの防止を徹底:
  - AI モジュール・研究モジュールのすべてが内部で datetime.today()/date.today() を参照せず、外部から target_date を受け取る設計。
- フェイルセーフ動作:
  - AI API の失敗時は例外を投げずフォールバック値（macro_sentiment=0.0 等）で継続することで、パイプライン全体の耐障害性を高める。
- テスト性:
  - OpenAI 呼び出しや環境自動読み込みをテスト時に置き換え／無効化できるフックを提供。

### Removed
- なし

### Security
- なし

<!--
注: 本 CHANGELOG はリポジトリ内のソースコード内容に基づいて推測して作成しています。
実際のリリースノート作成時はコミット履歴やリリース管理情報を参照して調整してください。
-->