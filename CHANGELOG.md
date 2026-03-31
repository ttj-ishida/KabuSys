# Changelog

すべての注記は Keep a Changelog の形式に準拠します。  
このファイルにはパッケージのコードベース（初期リリース相当）の主要な追加・変更点や設計上の重要な振る舞いを、ソースコードから推測して日本語でまとめています。

全般的な方針
- ルックアヘッドバイアス防止のため、各処理は内部で datetime.today() / date.today() を直接参照しない設計になっています（呼び出し側から target_date を渡す方式）。
- DuckDB を主なデータ永続層として利用する想定。SQL と Python を組み合わせて処理を実装。
- 外部 API（OpenAI / J-Quants）呼び出しはフェイルセーフ設計。API 失敗時は例外を投げずに安全側の既定値（中立スコア等）へフォールバックするか、上位にわたるエラー情報を収集して伝搬します。
- ロギング・冪等性・トランザクション処理・エラーハンドリングに注力しています。

## [0.1.0] - 2026-03-31

### Added
- 基本パッケージ構成
  - パッケージ名: kabusys（バージョン 0.1.0）
  - メイン公開モジュール: data, strategy, execution, monitoring（__all__ でエクスポート）

- 環境設定管理（kabusys.config）
  - .env ファイル・環境変数を自動読み込み（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロードを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサーはコメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、および行内コメント（条件付き）に対応。
  - 環境変数保護（protected keys）をサポートし、override オプションで既存値を上書き可。
  - Settings クラスを提供（プロパティ経由で設定値を取得）。
    - J-Quants / kabuステーション / Slack / DB パス / システム設定等のプロパティを定義。
    - KABUSYS_ENV と LOG_LEVEL の値検証（許容値のチェック）を実装。
    - duckdb/sqlite パスはデフォルトを提供し Path オブジェクトで返却。

- AI 関連機能（kabusys.ai）
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約し、銘柄ごとに OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを算出。
    - 時間ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB と比較）。
    - バッチサイズ、1銘柄あたり記事数上限、文字数トリム等のトークン肥大対策を実装。
    - JSON Mode（厳密な JSON）を期待。レスポンスのパースとバリデーション処理を実装。
    - エラー耐性: 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ（リトライ）を実装。その他はスキップして継続。
    - スコアは ±1.0 にクリップ。最終的に ai_scores テーブルへ（DELETE → INSERT）で置換的に書き込む。
    - テスト容易性のため OpenAI 呼び出し部分は _call_openai_api をパッチ可能に設計。
    - DuckDB executemany の制約（空リスト不可）を考慮して、呼び出し側で空チェックを行う。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull / neutral / bear）を算出。
    - マクロニュースはキーワードフィルタで抽出（複数の日本語・英語キーワード群）。
    - OpenAI 呼び出しは JSON 出力を期待し、レスポンスのパース/検査を実施。API 失敗時は macro_sentiment=0.0 で継続（フェイルセーフ）。
    - 計算結果は market_regime テーブルへ冪等に（BEGIN / DELETE / INSERT / COMMIT）書き込む。
    - OpenAI クライアント生成時に API キーを引数で注入可能（テストしやすい）。

- データプラットフォーム（kabusys.data）
  - ETL パイプライン（kabusys.data.pipeline）
    - 差分更新、バックフィル、品質チェックとの連携を想定した ETLResult データクラスを導入（取得数・保存数・品質問題・エラーの集約）。
    - DuckDB 上での最大日付取得、テーブル存在チェック等のユーティリティを提供。
    - デフォルトのバックフィル・カレンダー先読みなど運用向け設定を実装。

  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを使った営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 登録値優先、未登録日は曜日ベースでフォールバック（週末を休日扱い）。
    - calendar_update_job により J-Quants API から差分取得して market_calendar を更新（バックフィル期間を含め恒常的に再取得し、訂正を取り込む）。
    - 最大探索日数や健全性チェック（未来日付の異常検出）を備え、異常時はスキップして安全側の振る舞いを保証。

- リサーチ・ファクター計算（kabusys.research）
  - factor_research モジュール
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離等を計算（データ不足時は None）。
    - calc_volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比率等を算出（ウィンドウ内のデータ不足を扱う）。
    - calc_value: raw_financials と prices_daily を組合せて PER / ROE を算出（EPS 0 / NULL は None）。
    - 全関数は prices_daily / raw_financials の参照に限定し、本番口座へアクセスしないことを明示。

  - feature_exploration モジュール
    - calc_forward_returns: 指定日から各ホライズン（デフォルト [1,5,21] 営業日）までの将来リターンを計算。ホライズンが無効（<=0 や >252）なら例外。
    - calc_ic: ファクター値と将来リターンの Spearman ランク相関（IC）を計算。データ不足（<3）なら None。
    - rank: 同順位は平均ランクで扱うランク関数（浮動小数丸め対策あり）。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を算出。

- 小さなユーティリティ
  - data/etl モジュールで ETLResult を再エクスポート。
  - ai パッケージは score_news（news_nlp）を外部へ公開、regime_detector も同梱。

### Changed
- （初期リリースのため大きな互換破壊はなし）  
  ただし、設計上の重要な挙動をドキュメント化:
  - API 失敗時のデフォルト挙動（ニュースマクロ: 0.0、スコア未取得銘柄はスキップ、DB 書き込みはトランザクションで保護）を明示。
  - DuckDB 互換性対応（executemany の空パラメータ回避）を組み込み、部分失敗時に他データを保護するための DELETE → INSERT の戦略を採用。

### Fixed / Robustness
- 各種フェールセーフ実装
  - OpenAI 呼び出しでの JSON パースエラー、キー欠如、不正値等は警告ログを残して安全側の値を返す。
  - レスポンスに余計な前後テキストが混ざった場合でも最外の { ... } を抽出して復元を試みる処理を実装（news_nlp のバリデーション）。
  - ネットワーク・レート制限・一時的なサーバー 5xx エラー対して指数バックオフで再試行。上限リトライ消費時はスキップまたは中立値を採用して継続。
  - 不足データ（価格や記事が少ない）に対する明確な挙動（ma200_ratio 中立値 1.0、ma200_dev 等は None）を実装。
  - DB 書き込み失敗時に ROLLBACK を試行し、それ自体が失敗した場合は警告ログを出す。

### Tests / 開発支援
- OpenAI 呼び出し部分はモジュール内の _call_openai_api を patch 可能に設計（unittest.mock.patch による差し替えを想定）。
- Settings による環境取得や api_key の注入などテストでの DI（依存注入）を想定した引数設計。

### Notes / Known behaviors
- OpenAI モデルは gpt-4o-mini を想定し、JSON Mode（response_format={"type": "json_object"}）での利用を前提としている。
- news_nlp のバッチ処理は 1 回あたり最大 20 銘柄（_Batch_size）で API へ送信する仕様。
- マクロニュース抽出や銘柄抽出のキーワード・ウィンドウはコード内定数で管理（変更により挙動が変わります）。

---

以上がソースコードから推測した初期リリース（0.1.0）の変更点・機能一覧です。  
補足やバージョン履歴の追記（将来の変更点追加）を希望される場合は、変更箇所の差分や追加ファイルを指定してください。