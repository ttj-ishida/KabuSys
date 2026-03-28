CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルはコードベースから推測して作成しています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-28
-------------------

Added
- 基本パッケージ初期実装を追加
  - パッケージ version: 0.1.0 (src/kabusys/__init__.py)

- 環境・設定管理 (src/kabusys/config.py)
  - .env/.env.local 自動読み込み機構を実装（プロジェクトルートを .git / pyproject.toml で探索）
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応
  - export 形式やクォート・インラインコメントのパースに対応した .env パーサ実装
  - 環境変数保護（既存 OS 環境変数を保護する protected セット）
  - Settings クラスを提供し、主要設定をプロパティ経由で取得可能に
    - 必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DB パス設定: DUCKDB_PATH, SQLITE_PATH（デフォルト path を指定）
    - 動作環境: KABUSYS_ENV（development / paper_trading / live のバリデーション）
    - ログレベル: LOG_LEVEL のバリデーション（DEBUG/INFO/...）

- AI ニュース関連 (src/kabusys/ai/news_nlp.py, src/kabusys/ai/regime_detector.py)
  - news_nlp:
    - raw_news と news_symbols を集約し、銘柄ごとにニュースをまとめて OpenAI（gpt-4o-mini）の JSON Mode で一括センチメント評価
    - バッチ処理（最大 20 銘柄/コール）、記事トリム（最大記事数・最大文字数）を実装
    - リトライ（429・ネットワーク・タイムアウト・5xx で指数バックオフ）とレスポンスバリデーション実装
    - レスポンスの validation/extraction、スコアの ±1.0 クリップ、ai_scores テーブルへの冪等的置換（DELETE → INSERT）
    - calc_news_window: JST ベースのニュース収集ウィンドウ計算ユーティリティを実装（テスト容易性のため datetime.today() を参照しない）
    - テスト向けに _call_openai_api を差し替え可能（unittest.mock.patch に対応）
  - regime_detector:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム ('bull'/'neutral'/'bear') を判定
    - ma200_ratio 算出（不足時は中立 1.0 をフォールバックし WARNING ログ）
    - マクロキーワードで raw_news をフィルタして LLM に渡す機能実装
    - OpenAI 呼び出しは独立実装、API エラー時のフォールバック（macro_sentiment=0.0）、再試行の制御、JSON パース保護
    - market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）とロールバック処理

- Data / ETL (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
  - ETLResult データクラスを実装して ETL の結果（取得/保存件数、品質問題、エラーなど）を集約
  - ユーティリティ: テーブル存在チェック / 最大日付取得等を実装
  - ETL の設計方針（差分更新、backfill、品質チェックの取り扱い、id_token 注入可能）をコードドキュメントに反映
  - etl モジュールで ETLResult を再エクスポート

- Data / カレンダー管理 (src/kabusys/data/calendar_management.py)
  - JPX マーケットカレンダー管理モジュールを実装
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days といった営業日判定ユーティリティ
    - market_calendar が未取得時の曜日ベース・フォールバック（週末を非営業日扱い）
    - DB 登録値優先、未登録日は曜日フォールバックで一貫した挙動
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等保存。バックフィル・健全性チェックを実装
  - DuckDB からの date 値変換ユーティリティを提供

- Research（ファクター・特徴量探索）(src/kabusys/research/*.py)
  - factor_research:
    - モメンタムファクター: mom_1m / mom_3m / mom_6m / ma200_dev（200日MA乖離）を計算する calc_momentum を実装
    - ボラティリティ / 流動性: ATR(20) / atr_pct / avg_turnover / volume_ratio を計算する calc_volatility を実装
    - バリューファクター: PER / ROE を raw_financials と prices_daily から結合して計算する calc_value を実装
    - DuckDB SQL ベースでの実装、データ不足時は None を返す設計
  - feature_exploration:
    - calc_forward_returns: 複数ホライズンに対する将来リターンを一度のクエリで取得（LEAD を使用）
    - calc_ic: スピアマンランク相関（IC）を実装し、欠損や ties の扱いを考慮
    - rank: 同順位の平均ランク処理（丸めで ties を検出する対策）
    - factor_summary: 各ファクターの count/mean/std/min/max/median を標準ライブラリのみで計算
  - research パッケージのエクスポート調整（主要関数を __all__ に列挙）

Changed
- 設計上の重要方針をコードドキュメント内で明確化
  - ルックアヘッドバイアス防止のため datetime.today()/date.today() を参照しない実装（target_date 引数ベース）
  - API 呼び出し失敗時はフェイルセーフ（例外を上げずにデフォルト値を使用）とする方針を各所で採用
  - DuckDB の互換性対応（executemany の空リスト回避や list 型バインドの回避）を反映

Fixed
- なし（初期リリース推測）

Security
- なし（ただし環境変数の取り扱い・保護設定を導入）

Notes / Implementation details
- OpenAI クライアントは gpt-4o-mini を想定し JSON Mode を利用する設計
- テスト容易性を意識して _call_openai_api をモジュールごとに差し替え可能にしている
- 各種 API 呼び出しはリトライ（指数バックオフ）・ステータスコード判定を行い、5xx 系はリトライ対象、その他はスキップの方針
- DB 書き込みは可能な限り冪等にし、部分失敗時に既存データを保護する（例: ai_scores は対象コードのみ上書き）
- ロギングと WARN/INFO の出力を豊富にし、失敗ケースでの診断を容易にしている

Breaking Changes
- なし（初期バージョン）

References / Required environment variables
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（API 使用時）などが必要

（注）この CHANGELOG はリポジトリ内のソースコードとドキュメンテーション文字列から推測して作成したものです。実際のリリースノート作成時はコミット差分やリリース管理方針に基づいて調整してください。