# CHANGELOG

このプロジェクトは Keep a Changelog の形式に従って変更履歴を管理します。主にコードベースから推測した初期リリース内容と設計上の注意点を記載しています。

全般的な注記
- 日時の扱いはルックアヘッドバイアス防止のため、内部で datetime.today() / date.today() を不用意に参照しない設計になっています（関数は target_date 等を引数で受け取る）。
- DuckDB を主要な永続層として利用しています。SQL はパフォーマンスと互換性を考慮した実装になっています。
- OpenAI（gpt-4o-mini）を用いた NLP 処理は JSON Mode を利用し、レスポンスのバリデーション・リトライ・フェイルセーフ（API失敗時はスコアを 0 にフォールバック）を組み込んでいます。
- .env 自動ロード機能を備え、プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を読み込みます。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能です。

Unreleased
- （なし）

[0.1.0] - 2026-03-31
Added
- パッケージ全体
  - 初期パッケージ構成を追加（kabusys パッケージ、サブパッケージ: data, ai, research 等の骨組み）。
  - __version__ を "0.1.0" に設定。

- 環境・設定管理（kabusys.config）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルート探索、読み込み順: OS 環境 > .env.local > .env）。
  - export KEY=val 形式やシングル／ダブルクォート、行内コメントに対応する堅牢な .env パーサーを実装。
  - Settings クラスを導入し、J-Quants / kabuステーション / Slack / DB / 監視閾値等の設定をプロパティ経由で取得。
  - 環境値検証（KABUSYS_ENV の許容値、LOG_LEVEL の許容値）を追加。

- AI モジュール（kabusys.ai）
  - news_nlp.score_news:
    - raw_news と news_symbols を集約し、銘柄ごとに最大記事数・文字数でトリムして OpenAI にバッチ送信する処理を実装。
    - バッチ処理（最大 20 銘柄 / リクエスト）・JSON Mode 利用・レスポンス検証（構造・型チェック・既知コードのみ取り込み）を実装。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフのリトライ実装。
    - DuckDB への書き込みは部分置換（対象コードのみ DELETE → INSERT）し、部分失敗時に既存データを保護する設計。
    - テスト容易性のため _call_openai_api をモック差し替え可能。

  - regime_detector.score_regime:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して market_regime テーブルに冪等的に書き込む処理を実装。
    - マクロニュース抽出（キーワードフィルタ）・OpenAI 呼び出し（gpt-4o-mini）とリトライ・フェイルセーフを実装。
    - レジームスコアの閾値に基づき 'bull' / 'neutral' / 'bear' を判定。
    - DB 書き込みは BEGIN/DELETE/INSERT/COMMIT の冪等方式。エラー発生時は ROLLBACK を試行して上位へ例外伝播。

- Data モジュール（kabusys.data）
  - calendar_management:
    - market_calendar を使った営業日判定ユーティリティを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録値優先、未登録日は曜日（土日）フォールバックする一貫した挙動。
    - calendar_update_job を実装（J-Quants から差分取得して保存、バックフィルと健全性チェックを含む）。
  - pipeline / etl:
    - ETLResult データクラスの追加（ETL 実行結果の整形、品質チェック結果・エラー一覧の保持）。
    - ETL パイプラインの設計方針（差分更新、バックフィル、品質チェックの考え方）を実装下地として追加。
    - DuckDB でのテーブル存在チェックなどのユーティリティを実装。
  - etl モジュールから ETLResult を再エクスポート。

- Research モジュール（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算する関数を追加。データ不足時の None 処理を実装。
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率等を計算する関数を追加。
    - calc_value: raw_financials から最新の財務指標を取得し PER / ROE を計算する関数を追加。
  - feature_exploration:
    - calc_forward_returns: 複数ホライズンの将来リターンを一度に取得する機能を追加（ホライズン入力検証あり）。
    - calc_ic: スピアマンランク相関（IC）を計算するユーティリティを追加（レコード結合・欠損除外・最小サンプルチェック）。
    - rank: 同順位は平均ランクで扱うランク付け実装（丸めによる ties 対策あり）。
    - factor_summary: 各ファクターの count/mean/std/min/max/median を計算する集計ユーティリティを追加。
  - research パッケージは data.stats の zscore_normalize を再エクスポート。

Changed
- （初期リリースのためメジャーな「変更」はありません。設計上の配慮やフェイルセーフが盛り込まれています）
  - API 呼び出し周りはエラー耐性を重視（特定の例外に対するリトライ、非 5xx やパースエラーではフォールバックして継続）。

Fixed
- （初期リリースのため「修正履歴」はなし）

Security
- 必須の外部 API キー（OpenAI 等）は Settings 経由で取得し、未設定時は明示的に ValueError を投げて早期検出するようにしています。

Deprecated
- なし

Removed
- なし

Notes / 既知の問題
- pipeline._get_max_date の末尾に不完全な行（`return date.fro` のような未完の戻り処理）が見られます。これは明らかにタイポ／未完成コードの痕跡で、ランタイムエラーを引き起こします。修正案:
  - 正しくは DuckDB から返る値を date に変換して返す必要があります（例: 値が date インスタンスならそのまま返し、文字列等なら date.fromisoformat を使う等）。
- 一部モジュール（例: data/__init__.py は空、strategy / execution / monitoring の実装参照があるが提示コードには未掲載）については実装の骨格のみまたは未公開のため、機能が揃っていない可能性があります。
- OpenAI 依存部分は API レスポンス形式や SDK のバージョン差異に影響を受ける可能性があります。テストでは _call_openai_api をモックすることが想定されています。

今後の推奨作業（提案）
- pipeline._get_max_date の不完全実装を修正してユニットテスト追加。
- data, strategy, execution, monitoring の欠落しているエントリポイントやユニットテストの整備。
- OpenAI 関連の統合テスト（API 変化や JSON Mode の挙動確認）と料金・レート管理に関する運用ドキュメントの追加。
- DuckDB バージョン差分による executemany の挙動（空リスト不可等）に関するテスト・ドキュメント化。

---
この CHANGELOG はコードベースの内容を解析して推測したもので、実際のコミット履歴とは異なる場合があります。必要であれば、各項目をより厳密にコミット単位で分解して記載できます。