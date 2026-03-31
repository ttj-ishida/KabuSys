# CHANGELOG

すべての重要な変更をここに記録します。本ファイルは「Keep a Changelog」形式に準拠しています。

- 変更は重要度順（Added / Changed / Fixed / Security 等）で記載します。
- 日付はリリース日です。

## [Unreleased]
（現在のリポジトリ状態での未リリース変更はありません）

## [0.1.0] - 2026-03-31
初回リリース。日本株自動売買システムのコアライブラリを提供します。主な追加点と設計上の特徴は以下の通りです。

### Added
- パッケージ基盤
  - kabusys パッケージ初期化（__version__ = "0.1.0"）。
  - パッケージ公開モジュール一覧: data, strategy, execution, monitoring を __all__ で定義。

- 設定・環境管理（kabusys.config）
  - .env ファイルおよび環境変数からの設定読み込みを実装。
  - プロジェクトルート検出ロジック: .git または pyproject.toml を基準に探索（CWD 非依存）。
  - .env ファイル自動ロード（優先順位: OS 環境 > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用途）。
  - .env パーサ実装（export プレフィックス対応、シングル/ダブルクォート・バックスラッシュエスケープ・インラインコメントの取り扱い）。
  - 環境変数上書きロジック（override / protected による保護）を実装。
  - Settings クラスを提供。J-Quants・kabuステーション・Slack・DB パス・実行環境（development/paper_trading/live）・ログレベルの取得・バリデーションを含む。

- AI 関連（kabusys.ai）
  - news_nlp モジュール
    - raw_news と news_symbols を基に銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）に JSON モードでバッチ評価を依頼して ai_scores テーブルへ書き込み。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で提供。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄）、1銘柄あたり記事数・文字数トリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - レート制限・ネットワーク断・タイムアウト・5xx を対象に指数バックオフでリトライ。
    - レスポンス検証ロジック（JSON 抽出、results 配列の検証、code/score の正規化・型チェック、スコアのクリップ）。
    - テスト容易性のため OpenAI 呼び出し部分を差し替え可能（ユニットテスト向け patch ポイントあり）。
    - API 失敗時もフェイルセーフで処理を継続し、部分成功時は成功した銘柄のみ DB 更新（部分失敗で他銘柄のスコアを上書きしない設計）。

  - regime_detector モジュール
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次市場レジーム（bull/neutral/bear）を判定。
    - ma200_ratio 計算（ルックアヘッド防止のため target_date 未満データのみ使用）。データ不足時は中立（1.0）にフォールバック。
    - マクロニュース抽出（マクロキーワードリストを使用）→ OpenAI により macro_sentiment を算出（JSON の厳密出力を期待）。
    - OpenAI 呼び出しは専用関数を用意し、news_nlp とは独立（モジュール間結合を最小化）。
    - API 失敗時は macro_sentiment = 0.0 で継続。冪等性を考慮した DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - リトライ（最大回数・指数バックオフ）、5xx の扱いに対する細かな分岐を実装。

- データ基盤（kabusys.data）
  - ETL パイプライン（pipeline モジュール）
    - ETLResult データクラスの公開（ETL 実行結果の構造化: 取得数/保存数/品質問題/エラー情報）。
    - テーブル存在チェックや最大日付取得などの内部ユーティリティを実装。
    - 差分更新・バックフィル・品質チェックの考え方をコード上で反映。

  - カレンダー管理（calendar_management モジュール）
    - JPX カレンダーの夜間バッチ更新ジョブ calendar_update_job（J-Quants API からの差分取得 ⇒ market_calendar へ冪等保存）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定 API を提供。
    - DB にカレンダーがない場合は曜日ベースのフォールバック（週末除外）で一貫した振る舞いを実現。
    - バックフィル、先読み、健全性チェック（未来日付が過度に大きい場合のスキップ）を実装。
    - jquants_client による fetch/save 呼び出しを利用（外部クライアントを抽象化）。

- 研究用ユーティリティ（kabusys.research）
  - factor_research モジュール
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR、相対 ATR、出来高比）、Value（PER、ROE）等のファクター計算を実装。
    - DuckDB 上の SQL とウィンドウ関数を活用して効率的に値を算出。
    - データ不足時の None 扱い、ログ出力を行う。

  - feature_exploration モジュール
    - 将来リターン計算（calc_forward_returns）、IC（Spearman ランク相関）計算（calc_ic）、ランク変換（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等外部依存を避け、標準ライブラリと DuckDB の SQL のみで実装。
    - 入力検証（horizons の範囲チェック等）を実施。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし。ただし多くのフェイルセーフ・エッジケース処理（APIエラー時フォールバック、JSON パース時の余分テキスト抽出、DuckDB executemany の空リスト回避など）を設計段階で導入済み）

### Security
- 環境変数の取り扱いにおいて、OS 側の既存環境変数を保護するため protected キーセットを使用（.env 読み込みで上書きを制御）。
- OpenAI API キー等の必須値は Settings から明示的に要求し、未設定時は ValueError を送出。

### Design / Notes
- ルックアヘッドバイアス対策として、date や datetime の参照において datetime.today() / date.today() を直接利用しない実装方針を採用（target_date ベースで計算）。
- OpenAI 呼び出し部はユニットテストで容易にモック可能な形で実装（差し替えポイントを明示）。
- DB 書き込みは冪等性・部分失敗時のデータ保護を重視（DELETE→INSERT や個別 DELETE の採用など）。
- DuckDB のバージョン差異対応（executemany の空リスト回避、日付型ハンドリング等）を考慮した実装。

---

（注）この CHANGELOG は提供されたコードから推測してまとめた初期リリース記録です。実際の API クライアント実装（jquants_client 等）、外部依存関係、運用ルールに応じて追補・修正してください。