CHANGELOG
=========

すべての注目すべき変更点を記録します。  
このファイルは「Keep a Changelog」形式に従っており、セマンティクスは次のとおりです：Added / Changed / Fixed / Deprecated / Removed / Security。

現在のパッケージバージョン: 0.1.0

Unreleased
----------
（未リリースの変更はここに記載します）

[0.1.0] - 2026-04-03
-------------------

初期リリース — 日本株自動売買／リサーチ／データ基盤ライブラリ

Added
- パッケージ基本構成を追加
  - パッケージ名: kabusys、__version__ = "0.1.0"。
  - 公開サブパッケージ: data, research, ai, execution, strategy, monitoring（__all__ に基づく）。

- 環境設定管理（kabusys.config）
  - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で探索）。
  - .env / .env.local の読み込み順序と override / protected（OS環境変数保護）をサポート。
  - .env の行パーサを実装（export プレフィックス対応、シングル/ダブルクォート・エスケープ、インラインコメント識別）。
  - 自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD フラグに対応（テスト向け）。
  - 必須環境変数取得用の _require と Settings クラスを実装。
  - J-Quants / kabuステーション / LINE / DB パス / 監視閾値 / ログレベル / 環境種別（development/paper_trading/live）等の設定プロパティを提供。
  - 環境値の妥当性チェック（KABUSYS_ENV, LOG_LEVEL）を実装。

- データ層（kabusys.data）
  - ETL パイプライン概念と ETLResult 再エクスポート（pipeline.ETLResult）。
  - ETLResult（dataclass）: ETL 実行結果、品質チェック情報、エラー情報を格納し、辞書変換 to_dict を提供。
  - pipeline モジュール（差分取得、保存、品質チェック方針とユーティリティ）を実装。
  - calendar_management: JPX カレンダー管理ロジック（market_calendar の読み書き、営業日判定、next/prev/get_trading_days、is_sq_day）を実装。
    - market_calendar が未取得の際は曜日ベースのフォールバックを採用。
    - 夜間バッチ calendar_update_job を実装（J-Quants クライアント経由で差分取得、バックフィル、健全性チェック、冪等保存）。
  - ETL 用の内部ユーティリティ（テーブル存在確認、最大日付取得等）を提供。

- AI によるニュース解析 / レジーム判定（kabusys.ai）
  - news_nlp モジュール:
    - raw_news / news_symbols を集約し、銘柄ごとに前日15:00〜当日08:30（JST）ウィンドウのニュースをまとめて OpenAI にバッチ送信。
    - チャンク処理（最大20銘柄/チャンク）、1銘柄あたりの記事数・文字数上限（トリム）を実装。
    - OpenAI 呼び出しのリトライ（429、ネットワーク、タイムアウト、5xx に対する指数バックオフ）。
    - レスポンスの厳密なバリデーション（JSON 抽出、results 配列、code と score、既知コードのみ採用、数値チェック、スコアクリップ）。
    - ai_scores テーブルへ「対象コードのみ」を削除→挿入する方式で置換（部分失敗時に既存データを保護）。
    - テスト容易化のため _call_openai_api を patch して差し替え可能。
  - regime_detector モジュール:
    - ETF 1321（日経225連動）の200日移動平均乖離（重み70%）とマクロニュースのセンチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロニュースは news_nlp.calc_news_window で定義されるウィンドウからマクロキーワードで抽出。
    - OpenAI 呼び出し（gpt-4o-mini）には独立実装を使用しモジュールの結合を回避。
    - API 失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - 200 日データ不足時は ma200_ratio を中立と見なす（1.0 とする）。
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）とロールバック処理。

- リサーチ（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、ma200 乖離を計算（DuckDB SQL 実装、データ不足ハンドリング）。
    - calc_volatility: 20日 ATR、相対ATR、出来高・売買代金指標を計算。
    - calc_value: raw_financials から最新財務データを取得して PER / ROE を計算。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン後の将来リターンを一括取得（可変ホライズン、入力検証）。
    - calc_ic: スピアマンのランク相関（IC）計算（欠損・同値・最小サンプルチェックを実装）。
    - rank: 平均ランク方式で同順位を処理（丸めにより ties 検出の安定化）。
    - factor_summary: 基本統計（count/mean/std/min/max/median）を算出。
  - zscore_normalize を data.stats から再エクスポート（研究用ユーティリティ）。

- 汎用設計方針 / 実装上の配慮
  - DuckDB を主要なデータストアとして使用（クエリは prices_daily, raw_news, raw_financials, market_calendar, ai_scores, market_regime 等を参照）。
  - ルックアヘッドバイアス対策: datetime.today()/date.today() を直接参照しない実装（target_date に依存）。
  - API 呼び出しの堅牢化: リトライ、指数バックオフ、5xx と非5xx の分岐、JSON パース回復処理を重視。
  - DB 書き込みは冪等性を意識（DELETE→INSERT、ON CONFLICT の利用想定）、トランザクションとロールバックを明示的に扱う。
  - テスト容易性: OpenAI 呼び出しの差し替えポイント、環境ロード無効化フラグ等を用意。

Changed
- （初版のため変更履歴なし）

Fixed
- （初版のため修正履歴なし）

Deprecated
- （初版のため該当なし）

Removed
- （初版のため該当なし）

Security
- OpenAI API キーは引数で注入可能（api_key）か環境変数 OPENAI_API_KEY を参照。未設定時は明示的に ValueError を送出して誤使用を防止。

Notes / 既知の挙動
- news_nlp と regime_detector はそれぞれ独自に OpenAI 呼び出しラッパーを持ち、モジュール間でプライベート関数を共有しない設計（テスト時は個別にモック可能）。
- DuckDB executemany は空リスト渡しに制約があるため、空チェックを行ってから executemany を実行する実装になっている（互換性維持）。
- calendar_management は market_calendar が欠損している場合に曜日ベースのフォールバックを利用するため、厳密な暦データが必要な運用では事前に calendar_update_job を実行しておくことを推奨。

開発者向けメモ
- パッケージルート検出は __file__ を起点に親ディレクトリを走査するため、配布後も .env 自動読み込みが正しく動作する設計。ただしテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動ロードを抑止可能。
- ログは各モジュールで logger.getLogger(__name__) を利用。LOG_LEVEL の検証は Settings.log_level に実装済み。

---

このCHANGELOGはコードベースから推測して作成しています。実際のリリースノートや変更履歴として使う際は、実際のコミット履歴やリリース方針に合わせて調整してください。