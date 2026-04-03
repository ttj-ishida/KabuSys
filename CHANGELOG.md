# Changelog

すべての変更は「Keep a Changelog」形式に従い、重要度別（Added / Changed / Fixed / etc.）で記載しています。日付は本コードベースのスナップショット作成日です。

## [Unreleased]

- 現在未リリースの変更はありません。

## [0.1.0] - 2026-04-03

初回公開リリース。以下はコードベースから推測できる主要な機能・設計方針および実装上の注意点です。

### Added
- パッケージ基盤
  - kabusys パッケージを追加。パッケージバージョンは `0.1.0` に設定（src/kabusys/__init__.py）。
  - パッケージ公開 API のエントリ（data, strategy, execution, monitoring）を定義。

- 設定・環境管理
  - .env / 環境変数の自動読み込み機能を実装（src/kabusys/config.py）。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - 自動ロードを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` に対応。
    - プロジェクトルート検出は __file__ を起点に `.git` または `pyproject.toml` を探索（CWD に依存しない）。
    - .env パースは `export KEY=val` 形式、シングル/ダブルクォート内のエスケープ、インラインコメントの扱いなどに対応。
    - 環境変数の保護（OS 環境変数を protected として上書き回避）をサポート。
  - Settings クラスを公開し、アプリ設定（J-Quants / kabuステーション / LINE / DB パス / 監視設定 / システム環境フラグ等）をプロパティ経由で安全に取得可能にした。
    - 必須変数の未設定時は ValueError を送出する `_require` 実装。
    - KABUSYS_ENV と LOG_LEVEL の値検証を実装（許容値の検査）。

- データ処理・ETL
  - ETL 結果を表すデータクラス `ETLResult` を追加（src/kabusys/data/pipeline.py, re-export via src/kabusys/data/etl.py）。
    - 品質問題（quality.QualityIssue）の収集、エラー一覧、has_errors / has_quality_errors などのプロパティを提供。
  - ETL パイプライン設計に基づくユーティリティを実装（差分取得、バックフィル、品質チェックの枠組みを想定）。
  - DuckDB とのやり取りに配慮したユーティリティ（テーブル存在チェックや最大日付取得などの内部関数）。

- マーケットカレンダー管理
  - JPX カレンダー（market_calendar テーブル）を扱うユーティリティを実装（src/kabusys/data/calendar_management.py）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day の提供。
    - DB にデータがない場合は曜日ベースのフォールバック（週末は非営業日）を採用。
    - カレンダー夜間バッチ更新ジョブ `calendar_update_job` を実装。J-Quants から差分取得・バックフィル・健全性チェックを行い、冪等的に保存。
    - 最大探索日数制限やバックフィル日数、将来日付異常時のスキップなどの安全措置を実装。

- 研究（Research）モジュール
  - ファクター計算・特徴量探索機能を追加（src/kabusys/research/*）。
    - factor_research:
      - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を計算。
      - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率などを計算。
      - calc_value: PER（株価 / EPS）、ROE を raw_financials と prices_daily から計算。
      - DuckDB を用いた SQL ベース実装で、データ不足時は None を返す扱い。
    - feature_exploration:
      - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
      - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。
      - rank: 同順位は平均ランクで扱うランク変換ユーティリティを実装（丸め対策あり）。
      - factor_summary: count/mean/std/min/max/median の統計サマリーを提供。
    - 研究用 API は DuckDB 接続を受け取り、外部発注 API に影響を与えない設計。

- AI（ニュース NLP / レジーム判定）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約し、銘柄ごとにニュース本文をまとめて OpenAI（gpt-4o-mini）へ送信しセンチメントを取得。
    - タイムウィンドウは JST ベース（前日 15:00 ～ 当日 08:30 JST）を UTC に変換して扱う。calc_news_window を提供。
    - バッチ処理（最大 20 銘柄／API コール）、1銘柄あたりの記事数・文字数制限（トリム）を実装。
    - 再試行・指数バックオフ（429 / ネットワーク / タイムアウト / 5xx 対応）。API 失敗時は該当チャンクをスキップして継続。
    - レスポンスのバリデーション（JSON 抽出、results 配列、各要素の code/score、未知コード無視、数値検査）、スコアを ±1.0 にクリップ。
    - 書き込みは部分失敗に耐えるよう、取得したコードのみ DELETE → INSERT（トランザクション）で置換。
    - テスト容易性: OpenAI 呼び出しを差し替えやすい設計（内部 _call_openai_api を patch 可能）。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日 MA 乖離値（重み 70%）とマクロセンチメント（重み 30%）を合成して、日次で市場レジーム（bull / neutral / bear）を判定。
    - マクロセンチメントは raw_news のマクロキーワードでフィルタしたタイトル群を OpenAI（gpt-4o-mini）へ投げ、JSON レスポンスからスコア抽出。
    - ルックアヘッドバイアス回避: prices_daily のクエリは target_date 未満のデータのみを参照。内部で datetime.today()/date.today() を参照しない。
    - API 失敗時は macro_sentiment=0.0 とするフェイルセーフ。トランザクション（DELETE/INSERT/COMMIT）で market_regime へ冪等書き込み。
    - レトライ・バックオフ・5xx の扱いを実装。

- ロギング・可観測性
  - 各モジュールで詳細な logger 出力（info/debug/warning/exception）を実装し、失敗時のフォールバックや警告を明示。
  - トランザクション失敗時の ROLLBACK エラーを警告ログで捕捉。

### Changed
- 初回リリースのため、過去の変更履歴はありません。

### Fixed
- 初回リリースのため、明示的な修正履歴はありません。
  - 実装上、API レスポンスパース失敗やネットワークエラー時に例外を上位へ投げずフェイルセーフ（0.0 またはスキップ）で継続する設計が適用されている点は注意。

### Breaking Changes
- 初回リリースのため、互換性破壊はありません。

### Security
- 環境変数の扱いに注意:
  - 必須の秘密情報（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY など）は Settings 経由で取得し、未設定時は明示的に例外を送出。
  - .env ファイルの読み込みはデフォルトで有効。ただし自動ロードを明示的に無効化できる。
- OpenAI API 呼び出しタイムアウト・リトライ・エラーハンドリングを実装しているが、API キー管理やシークレット保護は利用者側で適切に行うこと。

### Notes / Implementation Details（重要な設計判断）
- ルックアヘッドバイアス回避: AI スコアやレジーム判定、ファクター計算等の主要ロジックはすべて target_date を明示的に受け取り、当日以降のデータを参照しない設計。
- DuckDB をデータ基盤として前提（DuckDB の executemany の空リスト制約など特性に配慮した実装）。
- OpenAI 呼び出しに対して JSON Mode を利用しつつ、万一前後に余計なテキストが混入した場合の復元ロジックを実装。
- 冪等性: market_calendar / ai_scores / market_regime への書き込みは既存レコードの削除 → 挿入（トランザクション）により冪等性を維持する方針。

---

（補足）本 CHANGELOG は提示されたコードベースの実装内容とドキュメント文字列から推測して作成しています。実際のリリースノート作成時はコミット履歴や変更差分、実際の運用上の注意点を反映してください。