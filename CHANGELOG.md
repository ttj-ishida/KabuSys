# CHANGELOG

このファイルは Keep a Changelog の形式に準拠しており、重要な変更点を分かりやすく記録します。  
Version タグと日付はコードベースから推測して記載しています。

すべての日付・内容はリポジトリの現状（src/kabusys 以下の実装）に基づく初期リリース想定の変更履歴です。

## [Unreleased]
- 今後のリリースに向けた作業項目をここに記載します。

## [0.1.0] - 2026-03-28
初期公開（推測）。以下の主要機能を実装・公開しました。

### 追加
- パッケージ構成
  - kabusys パッケージの基本エントリーポイントを追加（__version__ = 0.1.0）。
  - パッケージ公開モジュール群: data, strategy, execution, monitoring（__all__ にて指定）。

- 設定・環境変数管理（kabusys.config）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 読み込みの優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - .env パーサを堅牢化:
    - export KEY=val 形式対応
    - シングル/ダブルクォート中のエスケープ処理対応
    - インラインコメント処理（クォート外かつ '#' の前が空白/タブの場合のみコメントと扱う）
  - Settings クラスを提供し、主要設定（J-Quants, kabu API, Slack, DB パス, 環境種別・ログレベル判定等）をプロパティ経由で取得可能に。
  - 環境値の検証（KABUSYS_ENV の有効値検査、LOG_LEVEL 検査等）と必須値チェック（_require）を導入。

- データ関連（kabusys.data）
  - ETL パイプライン基盤（pipeline.ETLResult の公開）。
  - マーケットカレンダー管理（calendar_management）:
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ユーティリティ実装。
    - calendar_update_job による J-Quants からの差分フェッチ＆保存処理（バックフィル、健全性チェックを含む）。
    - DB 未取得日のフォールバックは曜日ベース（土日除外）で一貫性を確保。
  - ETL のユーティリティ:
    - DB テーブル存在チェック、最大日付取得、ETL 実行結果を表す dataclass (ETLResult) を追加。
    - ETLResult は品質チェック結果とエラー集合を含み、辞書変換 to_dict を提供（監査ログ用途）。

- ニュース NLP / AI（kabusys.ai）
  - news_nlp モジュール:
    - raw_news と news_symbols を基に銘柄別に記事を集約し、OpenAI（gpt-4o-mini）の JSON モードでバッチセンチメント評価を実行。
    - バッチ処理（最大 20 銘柄／回）、1 銘柄あたり記事数・文字数上限（トリム）を実装。
    - 再試行・エクスポネンシャルバックオフ（429, ネットワーク断, タイムアウト, 5xx 対象）。レスポンス検証とスコアの ±1.0 クリップ。
    - テスト用に _call_openai_api を差し替え可能に（patch しやすい設計）。
    - calc_news_window による JST ベースのニュース集計ウィンドウ計算を実装（ルックアヘッドバイアス回避）。
    - score_news: ai_scores テーブルへの冪等置換（DELETE → INSERT）を実装し、部分失敗時に既存データを保護。
  - regime_detector モジュール:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定。
    - マクロキーワードで raw_news をフィルタリングし、OpenAI でマクロセンチメントを評価（記事が無い場合は LLM 呼び出しをスキップし 0.0 フェイルセーフ）。
    - API 呼び出しに対する再試行、5xx の扱い、JSON パースの堅牢化（フォールバック）を実装。
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK を試行）。

- リサーチ / ファクター（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、ma200 乖離（ma200_dev）を計算。データ不足時の None 処理。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率等を計算。true_range の NULL 伝播制御。
    - calc_value: raw_financials の直近財務データと価格を組み合わせて PER, ROE を算出（EPS が 0/欠損の場合は None）。PBR・配当利回りは未実装。
    - 各関数は prices_daily / raw_financials のみ参照し、外部 API や発注系へアクセスしない安全設計。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons の入力検証あり。
    - calc_ic: スピアマンランク相関（Information Coefficient）を実装。データが不足（有効レコード < 3）時は None を返す。
    - rank: 平均ランク（同順位は平均ランク）を算出。丸めで ties の検出漏れを抑制。
    - factor_summary: count/mean/std/min/max/median の統計サマリーを提供。
  - research パッケージの公開 API:
    - calc_momentum, calc_volatility, calc_value, zscore_normalize（data.stats から再エクスポート）, calc_forward_returns, calc_ic, factor_summary, rank

### 変更（設計／安全性）
- ルックアヘッドバイアス回避:
  - AI とファクター計算の全実装で datetime.today()/date.today() を直接参照しない設計（呼び出し側が target_date を明示する方式）。
- DB 書き込みの冪等性確保:
  - ai_scores / market_regime 等への置換書き込みは DELETE→INSERT のパターンで部分失敗のデータ保護を行う。
  - トランザクション制御（BEGIN/COMMIT/ROLLBACK）を明示的に使用。
- テスト容易性:
  - OpenAI 呼び出しを行う内部関数を patch できるようにしてテストしやすくしている（_call_openai_api の差し替え）。
- フェイルセーフ方針:
  - AI API 失敗時は例外を上げずにゼロや空スコアで継続（ログ出力）することで、ETL/診断処理の安定性を優先。

### ドキュメント（コード内ドキュメンテーション）
- 各モジュールに詳細な docstring を追加し、処理フロー・設計方針・戻り値・例外・注意点を明記。

### 既知の未実装・制限（初期版）
- strategy / execution / monitoring の具体実装はこの差分からは確認できない（パッケージ公開名はあるが中身は別途実装想定）。
- jquants_client / quality モジュールへの依存点はあるが、それらの詳細実装は本差分に含まれない（外部クライアントの実装を前提）。
- 一部集計・保存処理は DuckDB のバージョンによるバインド挙動に依存するため、実行環境での互換性注意（コード内に回避策あり）。

## 参考（運用上の注意）
- OpenAI API キーは環境変数 OPENAI_API_KEY または関数の api_key 引数で指定する必要がある。未設定時は ValueError を送出する。
- .env パースは比較的堅牢だが、特殊なフォーマットの .env を使用する場合は事前確認推奨。
- calendar_update_job 等は外部 API (J-Quants) に依存するため、API エラー時はログ出力して 0 を返す（失敗に対して安全に継続）。

---

(注) 本 CHANGELOG は提供されたソースコードから実装意図を推測して作成した変更履歴です。実際のリリースノートやバージョン管理履歴が存在する場合は、そちらを優先してください。