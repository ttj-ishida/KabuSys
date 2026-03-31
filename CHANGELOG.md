# CHANGELOG

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

[Unreleased]
- （なし）

[0.1.0] - 2026-03-31
-------------------

Added
- パッケージ初期リリース。
- 基本パッケージ構成を追加:
  - kabusys (バージョン 0.1.0)
  - サブパッケージ: data, research, ai, monitoring, strategy, execution（__all__ で公開）
- 環境設定:
  - kabusys.config
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動ロードする機能を実装。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - export KEY=val 形式やクォート・エスケープ、行末コメントの扱いに対応した .env パーサーを実装。
    - Settings クラスを提供し、JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須値取得と、DUCKDB_PATH / SQLITE_PATH / KABUSYS_ENV / LOG_LEVEL 等の既定値・検証を行うプロパティを実装。
    - 未設定の必須環境変数取得時は ValueError を送出。

- AI（自然言語）:
  - kabusys.ai.news_nlp.score_news
    - raw_news / news_symbols を集約して銘柄ごとにニュースを連結し、OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信して銘柄別センチメント（-1.0〜1.0）を算出。
    - チャンク処理（デフォルト最大20銘柄/チャンク）、記事トリム（記事数上限・文字数上限）を実装。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフによるリトライ実装。その他エラーはスキップ（フェイルセーフ）。
    - レスポンスの厳密なバリデーションと数値クリッピング（±1.0）。
    - スコア書き込みは部分失敗時に既存データを保護する形で DELETE→INSERT（対象コードのみ）を実施。DuckDB の executemany 空リスト制約に配慮。
    - テスト容易性のため OpenAI 呼び出し関数を差し替え可能に実装（unittest.mock.patch を想定）。

  - kabusys.ai.regime_detector.score_regime
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュース由来の LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次で判定・保存。
    - マクロニュース抽出はマクロキーワードリストに基づくフィルタリング（最大 20 件）。
    - OpenAI 呼び出しは JSON モードで行い、失敗時は macro_sentiment=0.0 として継続（フェイルセーフ）。API の一時エラー・5xx に対してリトライ実装。
    - レジーム算出はスコアのクリップ後、しきい値によりラベル付与。market_regime テーブルへは冪等（BEGIN/DELETE/INSERT/COMMIT）で書き込み。

- データプラットフォーム:
  - kabusys.data.calendar_management
    - market_calendar を用いた営業日判定ユーティリティを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar が未取得の際は曜日ベース（土日休）でフォールバックする一貫したロジックを実装。
    - JPX カレンダーを J-Quants から差分取得して market_calendar を更新する夜間バッチ calendar_update_job を実装。バックフィルや健全性チェックを含む。
  - kabusys.data.pipeline / kabusys.data.etl
    - ETLResult データクラスを実装・公開（ETL 実行結果、品質チェックやエラー情報を保持）。
    - 差分更新、backfill、品質チェックに関する設計（ドキュメント準拠）を反映したユーティリティを実装。
    - DuckDB テーブル存在チェックや最大日付取得ユーティリティを実装。

- リサーチ（ファクター）:
  - kabusys.research.factor_research
    - calc_momentum: 1M/3M/6M リターン、および 200 日 MA 乖離（ma200_dev）を計算（データ不足時は None または中立扱い）。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算（データ不足時は None）。
    - calc_value: raw_financials を用いて PER / ROE を計算（EPS が 0 または欠損時は None）。
    - DuckDB を用いた SQL ベースの計算で外部 API に依存しない実装。
  - kabusys.research.feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
    - calc_ic: スピアマンのランク相関（IC）を計算するユーティリティ（レコード不足時は None）。
    - factor_summary: 各ファクターの count/mean/std/min/max/median を算出。
    - rank: 平均ランク（同順位は平均ランク）を返すユーティリティ。
  - kabusys.research.__init__ で主要関数群を再エクスポート。

- その他:
  - 各モジュールで DuckDB をデフォルトの分析 DB として使用する設計。
  - 全体として「ルックアヘッドバイアス防止」のため datetime.today() / date.today() に依存しない API 設計（target_date を明示的に受け取る関数群）。
  - OpenAI モデルはデフォルトで gpt-4o-mini を使用。JSON 出力モードを利用して厳密なパースを行う。
  - 多くの DB 書き込み処理でトランザクション（BEGIN/COMMIT/ROLLBACK）を採用し、失敗時にロールバックして上位へ例外を伝播。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- 環境変数で API キーを扱うことを前提にし、必要な値が未設定の場合は明示的に例外を出すことで誤操作を防止。

Notes / Implementation details
- テスト容易性: OpenAI 呼び出しを行う内部関数（各モジュールの _call_openai_api）はユニットテストで差し替え可能に実装。
- フェイルセーフ方針: 外部 API の一時障害やレスポンス不正時はスキップまたは中立値にフォールバックし、全体処理が致命的に停止しない設計。
- DuckDB の特性（executemany の空リスト禁止など）に対応するために条件分岐を設けている。

（注）この CHANGELOG は提供されたソースコードから推測して作成しています。実際のリリースノートとして使用する場合は、追加の変更点や内部仕様の差分を合わせて確認してください。