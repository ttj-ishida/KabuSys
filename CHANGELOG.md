# Changelog

すべての変更は Keep a Changelog の形式に準拠します。  
非互換な変更は明示します。

## [Unreleased]

## [0.1.0] - 2026-03-28
初回リリース。

### Added
- パッケージの基本構成を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 環境設定 / ロード機能（kabusys.config）
  - .env / .env.local を自動でプロジェクトルート（.git または pyproject.toml を検出）から読み込む自動ロード機能。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パーサは `export KEY=val` 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント等に対応。
  - OS 環境変数を保護するための protected キーを考慮した上書きロジック（`.env.local` は `.env` を上書き）。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 実行環境（development/paper_trading/live）/ログレベル等の取得を簡便化。
  - 必須環境変数未設定時は ValueError を送出する安全設計。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）でセンチメントを算出して `ai_scores` テーブルへ書き込む機能 `score_news` を実装。
  - 特徴:
    - JST ベースのニュースウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC で扱う）。
    - 1 銘柄あたり最大記事数・最大文字数でトリム（トークン肥大対策）。
    - 1 回の API 呼び出しで最大 20 銘柄（チャンク処理）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ。
    - OpenAI の JSON-mode を利用し、レスポンスのバリデーション・数値クリップ（±1.0）。
    - DuckDB に対する冪等な書き込み（対象コードのみ DELETE → INSERT）と DuckDB 0.10 互換性への配慮（executemany の空配列回避）。
    - API 失敗時はスキップして継続するフェイルセーフ設計（例外を上げず部分成功を許容）。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成し、market_regime テーブルへ書き込む `score_regime` を実装。
  - 特徴:
    - MA 計算は target_date 未満のデータのみ使用し、ルックアヘッドバイアスを排除。
    - マクロキーワードで raw_news をフィルタして LLM に渡す（上限記事数を設定）。
    - OpenAI 呼び出しは専用関数で抽象化。API エラー時は macro_sentiment=0.0 でフォールバック（フェイルセーフ）。
    - 冪等な DB 書き込み（BEGIN → DELETE → INSERT → COMMIT、失敗時は ROLLBACK）。

- ETL / Data 管理（kabusys.data.pipeline, kabusys.data.etl, kabusys.data.calendar_management）
  - ETLResult データクラスを公開（ETL 実行結果の集約、品質問題・エラーログの収集を想定）。
  - pipeline: 差分更新・バックフィル・品質チェックの方針を反映する設計（J-Quants 経由の差分取得・保存を想定）。
  - カレンダー管理:
    - `market_calendar` テーブルを利用した営業日判定、next/prev_trading_day、get_trading_days、is_sq_day を実装。
    - DB 登録がない日については曜日ベースでフォールバック（週末除外）。
    - calendar_update_job により J-Quants から差分取得し冪等保存（バックフィル、健全性チェックあり）。
    - 探索上限日数を設定して無限ループを防止。

- リサーチ / ファクター計算（kabusys.research）
  - ファクター計算関数を追加:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率等。
    - calc_value: PER / ROE（raw_financials から最新報告を取得して計算）。
  - 特徴:
    - DuckDB に対する SQL ベースの実装（prices_daily / raw_financials のみ参照）。
    - データ不足時は None を返す安全設計。
  - 特徴量解析ユーティリティ:
    - calc_forward_returns: 任意ホライズンの将来リターン取得（デフォルト [1,5,21]）。
    - calc_ic: スピアマンランク相関（Information Coefficient）計算（3 件未満は None）。
    - rank, factor_summary: ランク変換（同順位は平均ランク）、各種統計量の集計。
  - zscore_normalize を data.stats から再エクスポート。

- テスト・拡張性の配慮
  - OpenAI 呼び出し箇所を内部関数として分離しており、unittest.mock.patch による差し替えが容易。
  - JSON パースの復元ロジック（前後余計なテキストが混入した場合でも {} の抽出を試みる）を実装し現場の LLM 出力に寛容。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Security
- OpenAI API キーや各種トークンは Settings 経由で必須チェックを行い、未設定時は明示的にエラーを発生させる設計。

### Notes / Implementation details
- ルックアヘッドバイアス対策: いずれの AI / リサーチ処理も内部で datetime.today()/date.today() を直接参照せず、呼び出し側から target_date を与える設計。
- DuckDB 互換性: executemany に空リストを渡せないバージョンへの互換性処理を実装。
- フェイルセーフ: 外部 API（OpenAI、J-Quants 等）の失敗は局所的にログ出力してフォールバックまたは部分的スキップを行い、全体処理が停止しないようにしている。
- OpenAI モデル: gpt-4o-mini をデフォルトで使用（JSON mode を利用した厳密出力を要求）。

---

今後の予定（例）
- jquants_client の具体実装や認証フローの整備。
- 追加ファクター・ポートフォリオ構築・実行モジュール（strategy / execution / monitoring）の実装。
- 単体テスト・統合テストの拡充と CI パイプライン整備。