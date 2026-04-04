# Changelog

すべての注目すべき変更をこのファイルに記録します。  
このプロジェクトは [Keep a Changelog] の形式に従い、セマンティックバージョニングを使用します。

[Keep a Changelog]: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-04
初回リリース。日本株の自動売買／データプラットフォーム向けの基盤機能を提供します。

### Added
- 基本パッケージ構成
  - パッケージ名 kabusys、バージョン 0.1.0 を追加。
  - パッケージ公開インターフェースに data, strategy, execution, monitoring を含む。

- 環境設定 / .env 管理（kabusys.config）
  - .env および .env.local の自動読み込み。プロジェクトルートは .git または pyproject.toml を基準に探索。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用）。
  - 高度な .env 解析：
    - export プレフィックス対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理。
    - インラインコメント処理（クォート外での `#` を条件付きでコメント扱い）。
  - Settings クラスによる型付き設定取得（J-Quants/LINE/kabu API トークン、DB パス、監視閾値、環境・ログレベル判定など）。

- AI モジュール（kabusys.ai）
  - news_nlp.score_news: raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）で銘柄毎のセンチメント ai_score を算出して ai_scores テーブルへ書込む ETL。
    - JST 時間ウィンドウ計算（前日15:00～当日08:30 JST）を実装。
    - バッチ処理（最大 20 銘柄 / チャンク）、1 銘柄当たりの最大記事数/文字数制限。
    - JSON Mode 利用のレスポンス検証と数値クリップ（±1.0）。
    - 再試行（429/ネットワーク/タイムアウト/5xx）を指数バックオフで実装。
    - 部分成功時に既存の他銘柄スコアを消さない（対象コードのみ DELETE → INSERT）。
  - regime_detector.score_regime: ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成し、market_regime テーブルへ日次で書き込み。
    - prices_daily から ma200_ratio を算出（ルックアヘッド防止で target_date 未満のみ使用）。
    - raw_news からマクロキーワードでフィルタしたタイトルを抽出して LLM に投げる。
    - OpenAI 呼び出しに対する堅牢なリトライ、API 失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - レジームスコアを -1.0〜1.0 にクリップし、'bull'/'neutral'/'bear' を判定。DB 書込は冪等（BEGIN / DELETE / INSERT / COMMIT）。

- データプラットフォーム機能（kabusys.data）
  - calendar_management: JPX カレンダー管理（market_calendar テーブル）と営業日判定ユーティリティを追加。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - DB 登録がない日については曜日ベース（土日除外）でフォールバック。
    - calendar_update_job により J-Quants API から差分取得・バックフィル・健全性チェックを実装。
  - pipeline / ETL: ETLResult データクラスを公開（kabusys.data.pipeline.ETLResult を再エクスポート）。
  - ETL 基盤（kabusys.data.pipeline）:
    - 差分更新、バックフィル、品質チェック方針、J-Quants クライアント連携の土台実装。
    - ETL 実行結果を集約する ETLResult（品質問題リスト・エラーリスト・集計を保持）。

- リサーチ機能（kabusys.research）
  - factor_research: モメンタム（1M/3M/6M）、200 日 MA 乖離、ATR（20 日）、流動性指標、財務指標（PER/ROE）などのファクター算出関数を実装（DuckDB を利用）。
  - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）、rank（同順位は平均ランク）、factor_summary（基本統計量）を実装。
  - zscore_normalize は kabusys.data.stats から再エクスポート。

### Changed / Design decisions
- ルックアヘッドバイアス対策
  - 全ての分析・スコアリング関数は内部で datetime.today()/date.today() を参照せず、明示的な target_date を使用。
  - prices_daily クエリは target_date 未満（排他）を適切に扱い未来データ参照を回避。

- IDempotent / 部分失敗耐性
  - AI スコア・market_regime などの DB 書込は冪等性を意識（対象日の DELETE → INSERT を使用）。
  - score_news はコードを絞り込んで DELETE → INSERT を行い、部分失敗時に他コードの既存データを保持。

- API 呼び出しに対するフェイルセーフ
  - OpenAI エラー（429/接続/タイムアウト/5xx）に対しては再試行のうえ、最終的に失敗した場合はスコアを中立(0.0)やスキップとして処理を継続（例外を上げずサービス全体の停止を防止）。
  - API 呼び出し関連の内部関数はテスト時に差し替え可能に（unittest.mock.patch 用の明確なポイントを提供）。

- DuckDB 互換性対応
  - DuckDB 0.10 の executemany の制約に対応するため、空パラメータリストの executemany を避けるチェックを追加。
  - テーブル存在チェックや日付型変換ユーティリティを整備。

- 環境変数の検証強化
  - KABUSYS_ENV と LOG_LEVEL の許容値を明示し、無効値の場合は ValueError を発生させる（早期検知）。

- OpenAI モデル・プロンプト設計
  - gpt-4o-mini をデフォルトモデルに指定。JSON Mode を想定したプロンプトとレスポンス検証ロジックを実装。

### Fixed
- 不足データ時の挙動改善
  - MA200 計算や ATR 等でデータ不足時には中立値（1.0）や None を返すようにして上位処理での例外発生を回避。
  - raw_news / market_calendar が空のケースでの明示的ログ出力と安全なフォールバックを追加。

- エラー／ロールバック処理の堅牢化
  - DB 書込み失敗時に ROLLBACK を試み、ROLLBACK 自体が失敗した場合は警告ログを出す実装。
  - OpenAI レスポンスの JSON パース失敗やレスポンス形式不正に対するログ出力とスキップ処理を追加。

### Testing / Developer conveniences
- テスト容易性のため、OpenAI 呼び出しポイント（_call_openai_api）をモジュール毎に用意しパッチで差し替え可能に。
- Settings で環境変数が不足した際の明確なエラーメッセージを提供し、.env.example を参照する旨を示す。

### Security
- 特になし（初期リリース）

---

注記:
- 本 CHANGELOG はソースコードからの機能・設計方針の推測に基づき作成しています。実際のリリースノート作成時はコミット履歴・タグ付け日・変更差分に基づいて修正してください。