# Changelog

すべての注目すべき変更を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

- リリースノートは重要な変更点のみを列挙しています（実装の細かな内部改善は省略する場合があります）。

## [Unreleased]

## [0.1.0] - 2026-03-28

初回公開リリース。日本株自動売買プラットフォームのコアライブラリを実装しました。主な追加点は以下の通りです。

### Added
- パッケージ基礎
  - kabusys パッケージ初期バージョンを追加（__version__ = 0.1.0）。
  - package API 用に主要サブパッケージを公開: data, strategy, execution, monitoring。

- 設定管理（kabusys.config）
  - .env ファイルと環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env 読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env パーサを強化:
    - export KEY=val 形式対応
    - シングル／ダブルクォート内のバックスラッシュエスケープ処理
    - インラインコメント処理（クォートあり／なしのケースを考慮）
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 必須環境変数検査用の _require ユーティリティ。
  - 設定プロパティ（J-Quants、kabuステーション、Slack、DB パス、実行環境・ログレベル判定など）を提供。環境値の検証（有効な env 値・ログレベルのチェック）を実装。

- AI（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約して銘柄毎にニュースを結合し、OpenAI（gpt-4o-mini）でセンチメント評価を行う score_news を実装。
    - JST ベースのニュースウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を提供（calc_news_window）。
    - バッチ処理（最大 20 銘柄／回）、記事数・文字数制限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - JSON Mode を利用した出力検証と堅牢なレスポンスパースロジック（余分な前後テキストの復元処理を含む）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフによるリトライとフォールバック（失敗時は該当チャンクをスキップして継続）。
    - DuckDB への冪等的な書き込み（DELETE → INSERT、executemany の空リストを避ける処理）。
    - テスト容易性のため _call_openai_api を差し替え可能に実装。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull / neutral / bear）を判定する score_regime を実装。
    - OpenAI 呼び出し（gpt-4o-mini）を用いたマクロセンチメント評価（_score_macro）。
    - API のリトライ/バックオフ、500 系の特別扱い、フェイルセーフ（API 失敗時に macro_sentiment=0.0）。
    - 決定結果は market_regime テーブルへ冪等的にトランザクションで書き込み（BEGIN/DELETE/INSERT/COMMIT）し、失敗時は ROLLBACK を試行。
    - ルックアヘッドバイアスを避ける設計（target_date 未満のみ参照、datetime.today()/date.today() を直接参照しない）。

- データ基盤（kabusys.data）
  - ETL パイプライン（kabusys.data.pipeline）
    - 差分取得・保存・品質チェックを想定した ETLResult データクラスを実装（取得件数、保存件数、品質問題、エラー一覧などを保持）。
    - DuckDB ベースでのテーブル存在チェック、最大日付取得ユーティリティ等を提供。
    - backfill 周り・カレンダー先読みに関する定数と設計方針を実装。
  - ETL の公開インターフェースとして ETLResult を再エクスポート（kabusys.data.etl）。
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar を元に営業日判定、前後営業日の取得、期間内営業日リスト取得、SQ 日判定関数を提供（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 登録データ優先、未登録日は曜日ベースでフォールバックする一貫したロジックを実装。
    - 夜間バッチ calendar_update_job を実装（J-Quants API から差分取得 → save → バックフィル・健全性チェックを含む）。
    - 最大探索日数を設定して無限ループを防止。

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR 等）、バリュー（PER、ROE）を計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB SQL を活用した高速集計、データ不足時の None 処理。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns、可変ホライズン対応）、IC（Spearman ランク相関を計算する calc_ic）、ランク化ユーティリティ（rank）、統計サマリー（factor_summary）を実装。
    - pandas 等の外部依存を使わず標準ライブラリと DuckDB で実装。
  - データ系ユーティリティ（zscore_normalize 等）を再エクスポート。

- その他
  - DuckDB を主要な分析 DB として利用する実装を一貫して採用。
  - OpenAI クライアント呼び出しは直接 SDK（OpenAI(...)）を生成する形で統一。テスト時に差し替えやすい設計。
  - ルックアヘッドバイアス対策（date 検索における排他条件や target_date 未満の限定など）を全モジュールで徹底。

### Changed
- （初回リリース）なし

### Fixed
- （初回リリース）なし

### Removed
- （初回リリース）なし

### Security
- OpenAI API キーは引数経由または環境変数 OPENAI_API_KEY で解決。キー未設定時は ValueError を発生させ安全に停止。

---

注記（開発者向け）
- 多くの外部 API 呼び出し部分（OpenAI / J-Quants クライアント）は例外耐性を考慮して実装されており、失敗時は部分的にフォールバックして全体処理を継続する方針です。必要に応じて上位で失敗検知・再実行を行ってください。
- テスト容易性のため、OpenAI 呼び出し等の内部ヘルパー関数はモック/パッチ可能な形で実装されています（例: unittest.mock.patch(...) で _call_openai_api を差し替え）。

--- 

参照: 本 CHANGELOG はコードベース（kabusys パッケージ、src/kabusys 配下）から推測して作成しています。必要であれば、各機能ごとにより詳細な変更点（例: SQL スキーマ、関数署名、戻り値仕様）を追記します。