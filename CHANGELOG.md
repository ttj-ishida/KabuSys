# CHANGELOG

すべての notable な変更点をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。  
バージョン番号は PEP 440 準拠です。

## [Unreleased]

## [0.1.0] - 2026-04-03
初回リリース。日本株自動売買・データ基盤・リサーチ用のコアライブラリを提供します。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - kabusys パッケージ初期化（バージョン: 0.1.0）。__all__ と __version__ を公開。

- 設定・環境変数管理
  - 環境変数自動ロード機構を実装（プロジェクトルート検出: .git / pyproject.toml）。.env / .env.local を OS 環境変数にマージ。
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - .env パーサの実装:
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメント扱いのルール、安全なコメント切り取りなど。
  - Settings クラスを提供（settings インスタンス経由でアクセス）:
    - J-Quants / kabu API / LINE / DB パス / 監視設定 / システム設定（環境・ログレベル）などのプロパティを定義。
    - 必須キー未設定時は ValueError を発生。
    - KABUSYS_ENV と LOG_LEVEL の値チェック（許容値セットを検証）。
    - デフォルト DB パス（duckdb/sqlite）や監視用閾値等のデフォルト値を定義。

- データ基盤（data）
  - calendar_management:
    - JPX マーケットカレンダー管理と営業日判定ユーティリティを提供。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days といった一貫した API。
    - market_calendar が部分的にしかない場合の曜日ベースのフォールバック、最大探索日数による保護、バックフィルや健全性チェックを実装。
    - calendar_update_job により J-Quants API から差分取得して冪等保存。
  - pipeline / ETL:
    - ETLResult データクラスを公開（ETL 実行結果の構造化）。
    - ETL パイプライン設計（差分更新、backfill、品質チェックの呼び出し方針等）を実装（pipeline モジュールに基礎実装、jquants_client / quality と連携する想定）。
    - DuckDB に対する存在チェック・最大日付取得などのユーティリティ。

- AI モジュール（ai）
  - news_nlp:
    - raw_news と news_symbols を集約して銘柄毎にニュースを結合し、OpenAI（gpt-4o-mini）でセンチメントを計算。
    - バッチ処理（最大 20 銘柄/チャンク）、記事/文字数トリム、JSON Mode を使ったレスポンス検証、リトライ（429/ネットワーク/5xx に対する指数バックオフ）。
    - レスポンスバリデーションとスコアクリップ（±1.0）、部分失敗時の既存スコア保護（対象コードのみ DELETE → INSERT）。
    - テスト用フック: _call_openai_api をモック可能。
    - calc_news_window: JST の定義（前日 15:00 ～ 当日 08:30）を UTC naive datetime に変換するユーティリティ。
  - regime_detector:
    - ETF 1321（日経225連動型）200日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）判定を行う機能を実装。
    - マクロ記事抽出（キーワードリスト）、OpenAI 呼び出し（gpt-4o-mini）によるマクロセンチメント評価、リトライとフェイルセーフ（API 失敗時は macro_sentiment=0.0）。
    - レジームスコアを clip し、market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。ルックアヘッドバイアス防止のため日付フィルタリング設計。
    - テスト用フック: _call_openai_api をモック可能。

- リサーチ（research）
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金、出来高変化率）、バリュー（PER, ROE）を計算する関数を提供（DuckDB+SQL ベース）。
    - データ不足時の None 扱い（安全設計）。
    - 計算は prices_daily / raw_financials テーブルのみ参照し、本番 API にはアクセスしない設計。
  - feature_exploration:
    - 将来リターン計算（複数ホライズン対応、horizons の入力検証）、IC（Spearman の ρ）計算、ランク変換ユーティリティ、ファクター統計サマリーを実装。
    - 外部依存を排し標準ライブラリで完結する実装方針。

- 汎用エラー処理・ロギング
  - 各モジュールで詳細なログ出力を実装し、API エラー時の挙動（警告・フォールバック・例外伝播）を明確に実装。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Deprecated
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Security
- 初回リリースのため該当なし。

Notes:
- OpenAI API の使用は外部サービスへの依存を伴うため、本パッケージは API キー（OPENAI_API_KEY）を要求します。api_key 引数での注入や、news_nlp/regime_detector 内の _call_openai_api のモックによりテスト容易性を考慮しています。
- データベースは DuckDB を前提とした設計です。DuckDB の executemany の制約（空リスト不可）等に配慮した実装が含まれます。

--- 

（今後のリリースでは、機能追加・パフォーマンス改善・API 互換性・セキュリティ対応を追記します。）