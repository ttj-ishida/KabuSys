# Keep a Changelog — CHANGELOG.md

すべての非互換な変更はバージョン番号で管理します。  
このファイルは Keep a Changelog の形式に準拠します。

フォーマット:
- 追加 (Added)
- 変更 (Changed)
- 修正 (Fixed)
- 非推奨 (Deprecated)
- 削除 (Removed)
- セキュリティ (Security)

## [Unreleased]

## [0.1.0] - 2026-03-31
最初の公開リリース。日本株自動売買システム「KabuSys」のコアモジュール群を追加。

### Added
- パッケージ初期化
  - kabusys パッケージの __version__ を "0.1.0" に設定。パッケージの公開エントリとして data / strategy / execution / monitoring をエクスポート。

- 設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env 読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env パーサーの実装: コメント、export 構文、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントの扱いを考慮。
  - .env 読み込み時の上書き制御（override）と OS 環境変数保護（protected）に対応。
  - 多数の設定プロパティを提供（J-Quants / kabuステーション / Slack / DBパス / 監視閾値 / 環境モード / ログレベル等）。
  - 必須環境変数未設定時に ValueError を送出する _require ヘルパーを実装。
  - 自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。

- AI モジュール (kabusys.ai)
  - news_nlp: ニュース記事を OpenAI (gpt-4o-mini) でスコアリングし、ai_scores テーブルへ書き込む機能を実装。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）と記事集約ロジック。
    - バッチ処理（最大 20 銘柄 / チャンク）、チャンク内での記事結合・トリム、トークン肥大化対策。
    - OpenAI 呼び出しは JSON mode を利用。429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ。
    - レスポンスバリデーション（results キー・型・既知コード・数値チェック）、スコアを ±1.0 にクリップ。
    - 部分失敗に備え、書き込みは対象コードのみ DELETE → INSERT する冪等更新。
    - テスト容易性のため内部 OpenAI 呼び出し関数を patch 可能に設計。
  - regime_detector: ETF（1321）の 200 日移動平均乖離とニュース由来のマクロセンチメントを合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - ma200_ratio 計算（target_date 未満のデータのみ使用してルックアヘッド防止）。
    - マクロキーワードによる raw_news 抽出（最大件数制限）。
    - OpenAI 呼び出し（gpt-4o-mini）でマクロセンチメントを取得。失敗時はフェイルセーフで 0.0 を採用。
    - レジームスコア合成ロジック（重みづけ: MA 70%、マクロ 30%）、閾値によるラベリング。
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。

- Research モジュール (kabusys.research)
  - factor_research: モメンタム / バリュー / ボラティリティ等の定量ファクター計算を実装。
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離などを計算。データ不足は None を返す。
    - calc_volatility: 20日 ATR、ATR/株価、20日平均売買代金、出来高比率等を計算。
    - calc_value: raw_financials から最新財務データを取得して PER / ROE を算出（EPS が 0 の場合は None）。
  - feature_exploration: 将来リターン計算・IC（Information Coefficient）・統計サマリー等を実装。
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを一括クエリで取得。
    - calc_ic: スピアマンランク相関（ランクベースの IC）を計算。有効レコードが 3 件未満の場合は None。
    - rank / factor_summary: ランク化（同順位は平均ランク）と統計サマリー（count/mean/std/min/max/median）。

- Data モジュール (kabusys.data)
  - calendar_management: JPX カレンダーの管理・営業日判定・夜間バッチ更新ジョブを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - market_calendar が未取得時の曜日ベースフォールバック、DB がまばらな場合でも一貫した判定を行う設計。
    - calendar_update_job: J-Quants API から差分フェッチして market_calendar を冪等更新。バックフィル・健全性チェックを実装。
  - pipeline / etl: ETL パイプライン用の ETLResult データクラスとユーティリティを追加。
    - ETLResult に品質チェック結果・エラー情報を含めて返却可能。
    - 差分更新・バックフィル・品質チェックの設計に準拠したインターフェース。
  - jquants_client / quality 等の外部クライアント利用を想定した実装箇所（クライアントは別モジュールで提供）。

- 実装方針・品質
  - ルックアヘッドバイアス防止のため、すべての処理において datetime.today()/date.today() を直接参照しない設計。
  - DuckDB を主要なストレージ/クエリ実行エンジンとして採用（SQL + Python の組合せ）。
  - 外部ライブラリ（pandas 等）に依存しない実装。
  - API 呼び出しや DB 書き込みでの冪等性・部分失敗耐性を考慮した設計。
  - ロギングを多用し、処理状況やフェイルセーフの理由を記録。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし（実装段階で堅牢性（パースの細かなケース、API リトライ戦略、DB 書き込みのロールバック等）に注意して実装）。

### Deprecated
- なし

### Removed
- なし

### Security
- OpenAI API キー（OPENAI_API_KEY）や各種トークン（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）は必須。未設定時には ValueError を送出する機能があるため、デプロイ前に適切に設定すること。
- .env 自動ロード機能はデフォルトで有効。テストや特殊環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能。

---

開発者向けメモ
- テスト容易性:
  - OpenAI 呼び出しはモジュール単位で置き換え可能（unittest.mock.patch を想定）に実装してあるため、外部 API をモックして単体テストを行いやすい。
- DuckDB のバージョン差異に依存しないよう実装上の注意（executemany の空リスト回避やリストバインド回避）を行っているため、運用時の互換性が高められている。
- 今後の追加予定:
  - strategy / execution / monitoring の具体実装（現状はパッケージとしてエクスポートのみ）
  - J-Quants / kabu ステーションのクライアント実装の拡充（認証・差分取得・保存ロジックなど）
  - その他ファクター・シグナルの追加検討

以上。