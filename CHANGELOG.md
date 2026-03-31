CHANGELOG
=========

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠して記載しています。

Unreleased
----------

（なし）

[0.1.0] - 2026-03-31
--------------------

Added
- 基本パッケージ初期リリース: kabusys 0.1.0
  - パッケージメタ情報:
    - src/kabusys/__init__.py にてバージョン "0.1.0" を定義。エクスポートモジュールは data, strategy, execution, monitoring を想定。

- 環境・設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して特定（CWD 非依存）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサの実装:
    - コメント行・export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理を考慮。
    - クォート無しの行では '#' の取り扱いを限定的にコメント判定。
  - 安全な読み込み挙動:
    - ファイルアクセス失敗時は warnings.warn を発行して処理継続。
    - OS 環境変数は protected として上書きを防止可能。
  - Settings クラスを提供（settings インスタンスで利用可能）:
    - J-Quants / kabuステーション / Slack / DB パス / 監視閾値等のプロパティを定義。
    - 必須環境変数未設定時は ValueError を送出する _require を実装。
    - KABUSYS_ENV, LOG_LEVEL の値検証（allowed 値セットをチェック）。
    - is_live / is_paper / is_dev 判定プロパティ。

- AI 関連機能 (src/kabusys/ai)
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols を集約し、銘柄毎にニュースをまとめて OpenAI（gpt-4o-mini）でセンチメントを評価。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄）で API を呼出し、JSON Mode 応答を期待。
    - 1 銘柄あたりの記事数・文字数上限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）でトークン肥大化を抑制。
    - 再試行戦略: 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ（_MAX_RETRIES）。
    - レスポンスのバリデーション (_validate_and_extract): JSON 抽出、"results" 構造・型チェック、未知コードの無視、スコアの数値化・有限性チェック、±1.0 クリップ。
    - DB 書き込みは冪等性を考慮（取得済みコードのみ DELETE → INSERT）。部分失敗時に既存スコアを保護。
    - テスト容易性: OpenAI 呼び出し部分は _call_openai_api を経由しており unittest.mock.patch で差し替え可。
    - 公開 API: score_news(conn, target_date, api_key=None) — スコアを書き込み、書き込んだ銘柄数を返す。
    - ニュースウィンドウ計算: calc_news_window(target_date)（JST 前日15:00〜当日08:30 を UTC ベースに変換）、ルックアヘッドバイアスを避ける設計。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジームを判定（'bull' / 'neutral' / 'bear'）。
    - prices_daily から MA200 乖離を厳密に target_date 未満のデータで計算（ルックアヘッド防止）。
    - raw_news からマクロキーワードで記事を抽出し、OpenAI（gpt-4o-mini）でマクロセンチメントを JSON 出力で取得。
    - API エラー時はマクロセンチメントを 0.0 にフォールバックするフェイルセーフ。
    - リトライ/バックオフ実装、API レスポンスパースの堅牢化、冪等な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）を採用。
    - 公開 API: score_regime(conn, target_date, api_key=None) — market_regime テーブルへ書き込み。

- リサーチ / ファクター計算 (src/kabusys/research)
  - factor_research モジュール:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日 MA 乖離）を DuckDB SQL で計算。
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率を計算（true_range の NULL 伝播を制御）。
    - calc_value: raw_financials から最新財務データを取得し PER / ROE を計算（EPS が 0/欠損の場合は None）。
    - 設計指針: DuckDB 接続のみ参照、ルックアヘッドを避ける、欠損データは None を返す。
  - feature_exploration モジュール:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。horizons の検証を実装。
    - calc_ic: スピアマンランク相関（IC）を実装。欠損/同値の扱い、最小サンプル数チェック（3 件未満で None）。
    - rank: 同順位は平均ランクにするランク化ユーティリティ（丸めで ties 検出漏れを抑制）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリ関数。
  - 研究ユーティリティの再エクスポート（src/kabusys/research/__init__.py）で主要関数を公開。

- データプラットフォーム関連 (src/kabusys/data)
  - calendar_management:
    - JPX カレンダー管理: market_calendar テーブルの参照/更新、営業日判定ロジック（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）。
    - DB にデータがある場合は DB 値を優先、未登録日は曜日ベースでフォールバック。
    - next/prev_trading_day は探索上限を設定し無限ループを防止（_MAX_SEARCH_DAYS）。
    - 夜間バッチ job: calendar_update_job(conn, lookahead_days) で J-Quants から差分取得・バックフィル・保存（健全性チェック、例外ハンドリングを備える）。
    - jquants_client（外部モジュール）経由でデータ取得/保存を行う想定。
  - ETL パイプライン (pipeline.py, etl.py):
    - ETLResult データクラスを導入し、ETL の集計結果・品質問題・エラー情報を格納。
    - ETL の設計方針（差分更新、バックフィル、品質チェック継続的収集、id_token 注入可能）を反映。
    - 一部ユーティリティ（テーブル存在確認・最大日付取得）を実装。
    - src/kabusys/data/etl.py で ETLResult を公開。

- ドキュメント的コメント・設計ノート
  - 各モジュールに対し、ルックアヘッドバイアス回避、冪等性、フェイルセーフ、テスト容易性（API 呼び出し差し替えポイント）、DuckDB 互換性に関する設計方針や注意ポイントを docstring とコメントで明記。

Changed
- 初回公開のため該当なし。

Fixed
- 初回公開のため該当なし。

Notes / Implementation details and safety measures
- OpenAI 呼び出し部分は共通的に JSON Mode に期待しており、レスポンスが不正な場合は慎重にパースしフェイルセーフで 0.0 や空スコアへフォールバックする実装。
- DB 書き込み時は BEGIN / COMMIT / ROLLBACK を明示的に扱い、失敗時にロールバックを試みたうえで例外を上位に伝播する方針。
- DuckDB の executemany に関する互換性を考慮し、空パラメータの渡し方に注意している（空リストは渡さない）。
- 時刻・日付はすべて date / datetime オブジェクトで扱い、タイムゾーン混入を避けるために UTC naive／JST 変換を明確化している。

今後の予定（含意）
- strategy / execution / monitoring など実行周りのモジュールはパッケージのエクスポートに含まれているが、今回のコードベースでは主にデータ取得・処理・研究・AI スコアリング周りの基盤が実装されています。運用（実注文）、監視エージェント、さらに詳細な ETL 実行フロー等は今後の作業で追加される見込みです。