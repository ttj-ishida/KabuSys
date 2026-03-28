# CHANGELOG

すべての変更は Keep a Changelog の慣例に従って記載しています。  
フォーマット: https://keepachangelog.com/（日本語訳に準拠）

## [Unreleased]
（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-03-28
初回公開リリース

### Added
- パッケージ初期版として kabusys を追加。
  - パッケージメタ情報: バージョン 0.1.0 を設定（src/kabusys/__init__.py）。
  - パッケージ API の公開モジュール: data, strategy, execution, monitoring を __all__ で公開。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート検出ロジック: .git または pyproject.toml を起点に探索（配布後の動作安定化）。
  - .env パースの強化:
    - 空行やコメント（#）無視、export KEY=val 形式対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応。
    - クォートなし行でのインラインコメント処理（直前が空白/タブの場合のみコメントとみなす）。
  - 自動ロードの優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - Settings クラスを実装し、J-Quants / kabu API / Slack / DB パス / 環境種別・ログレベルなどのプロパティを提供。
  - env・log_level に対するバリデーション（許容値チェック）を実装。

- AI モジュール（src/kabusys/ai）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約して銘柄ごとにニュースを結合し、OpenAI（gpt-4o-mini）でセンチメントを取得。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で提供。
    - バッチ処理（最大 20 銘柄／API コール）、記事数・文字数トリム、レスポンス検証、スコア ±1.0 でクリップ。
    - API の 429 / ネットワーク断 / タイムアウト / 5xx に対してエクスポネンシャルバックオフでリトライ。
    - レスポンスの部分失敗に対して他銘柄スコアを保護する（対象コードのみ DELETE→INSERT）。
    - DuckDB 互換性のため executemany 空リスト対策あり。
    - score_news(conn, target_date, api_key=None) を公開。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、日次で market_regime を算出・保存。
    - ma200_ratio 計算（target_date 未満のみ利用、データ不足時は中立値 1.0 を採用）。
    - マクロキーワードで raw_news をフィルタし、最大記事数を LLM に渡して JSON レスポンスから macro_sentiment を抽出。
    - OpenAI API 呼び出しのリトライ・フェイルセーフ（API 失敗時は macro_sentiment=0.0）。
    - レジームスコアを閾値で bull / neutral / bear に分類し、market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - score_regime(conn, target_date, api_key=None) を公開。

- Research モジュール（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比を計算。NULL / データ不足処理あり。
    - calc_value: raw_financials から最新財務を取得し PER / ROE を計算（EPS がない/0 の場合 PER=None）。
    - DuckDB 上の SQL とウィンドウ関数を活用する実装。

  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 任意ホライズンの将来リターンを一括で取得（horizons デフォルト [1,5,21]）。ホライズン検証あり。
    - calc_ic: スピアマンランク相関（Information Coefficient）を実装。有効データが少ない場合は None を返す。
    - rank: 同順位の平均ランクを返す関数（round(..., 12) による tie 回避）。
    - factor_summary: count/mean/std/min/max/median の統計サマリーを提供。
  - 研究用 API を __all__ で公開。

- Data モジュール（src/kabusys/data）
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days などの営業日判断ユーティリティを実装。
    - market_calendar がない場合の曜日ベースフォールバック（週末非営業日扱い）。
    - calendar_update_job: J-Quants API から差分取得・バックフィルを行い market_calendar を冪等保存。健全性チェックとバックフィルの実装。
    - DB に矛盾があった場合のログ出力や最大探索日数制限を導入。

  - ETL パイプライン（src/kabusys/data/pipeline.py, etl.py）
    - ETLResult データクラスを導入（取得数・保存数・品質問題・エラーの集約）。
    - 差分更新、バックフィル、品質チェックの方針を実装。_get_max_date などのユーティリティを提供。
    - jquants_client と quality モジュール経由でのデータ取得・保存を想定した設計。

  - データ API の公開: ETLResult を kabusys.data.etl で再エクスポート。

### Changed
- （初回リリースのため変更履歴なし）

### Fixed
- （初回リリースのため修正履歴なし）

### Security
- （本バージョンで特に報告するセキュリティ修正はありません）
  - 注意点として OpenAI API キーや各種トークンは Settings 経由で環境変数から取得する設計。KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動 .env 読み込みを無効化可能。

### Design / Implementation Notes (重要な設計判断)
- ルックアヘッドバイアス回避のため、日付参照に datetime.today() / date.today() を直接用いない設計。各関数は target_date 引数を受け取り、クエリも target_date 未満 / 以内の条件で慎重に扱う。
- DB 書き込みは冪等（DELETE → INSERT、ON CONFLICT など）かつトランザクション（BEGIN/COMMIT/ROLLBACK）で保護。
- OpenAI 呼び出しは JSON mode を用い厳密な JSON を期待、かつ API の一時障害に対してリトライ/バックオフを実装。パース失敗や API エラー時は例外を投げずフェイルセーフ（スコアを 0 にする、スキップする等）で処理継続。
- DuckDB の互換性（executemany に空リストを渡せない等）を考慮した実装ワークアラウンドを追加。
- 外部依存を抑え、DuckDB と標準ライブラリ中心で実装（pandas 等は未導入）。

---

今後のリリースでは以下を想定:
- strategy / execution / monitoring の具体的な実装拡充（現状はパッケージ公開のみ）
- テストカバレッジ増強とエンドツーエンド検証
- ドキュメント（使用手順、環境変数の例、DB スキーマ）追記

（必要であれば各モジュールごとのより詳細な変更点や設計メモを追記します。）