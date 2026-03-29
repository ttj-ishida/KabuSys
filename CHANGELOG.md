Keep a Changelog
=================

すべての重要な変更を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

フォーマット:
- 反映日は YYYY-MM-DD 形式で記載しています。
- 各リリースの変更はカテゴリ別（Added / Changed / Fixed / Deprecated / Removed / Security）で整理しています。

[Unreleased]
-----------

- なし

[0.1.0] - 2026-03-29
-------------------

Added
- パッケージ基盤を実装して初回リリース。
  - パッケージ情報:
    - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。
    - パッケージ公開用の __all__ を定義（data, strategy, execution, monitoring）。
- 環境変数／設定管理:
  - src/kabusys/config.py を追加。
  - .env/.env.local の自動ロード機能（プロジェクトルート自動検出）を実装。
  - .env パーサーはコメント、export プレフィックス、シングル/ダブルクォート、エスケープを扱える堅牢な実装。
  - OS 環境変数の保護（protected set）や override オプションをサポート。
  - 必須変数取得時に _require が ValueError を投げるチェック、環境値検証（KABUSYS_ENV / LOG_LEVEL の許容値）を実装。
  - デフォルトの DB パス（duckdb / sqlite）や Slack / kabu API / J-Quants の設定プロパティを提供。
- AI モジュール:
  - src/kabusys/ai/news_nlp.py を追加。
    - raw_news と news_symbols から銘柄別の記事を集約して OpenAI（gpt-4o-mini）にバッチ送信し、ai_scores テーブルへ書き込む機能を実装。
    - 処理ウィンドウ（JST基準 前日15:00〜当日08:30）計算ユーティリティ calc_news_window を提供。
    - スコアのバリデーション／クリッピング（±1.0）、レスポンスのリカバリ（JSON 部分抽出）、および冪等に配慮した DB 書き換えロジックを実装。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフによる再試行ロジックを実装。
    - テスト用に OpenAI 呼び出し箇所を差し替え可能（unittest.mock.patch を想定）。
  - src/kabusys/ai/regime_detector.py を追加。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、日次の市場レジーム（bull/neutral/bear）を判定して market_regime テーブルへ書き込む。
    - マクロキーワードでニュースを抽出し、OpenAI（gpt-4o-mini）を用いた JSON 出力パース、リトライとフォールバック（API 失敗時 macro_sentiment=0.0）を実装。
    - ルックアヘッドバイアス防止のため datetime.today() を直接参照しない設計。
- データプラットフォーム関連:
  - src/kabusys/data/calendar_management.py を追加。
    - JPX カレンダー管理（market_calendar）用ユーティリティ群を実装:
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
    - market_calendar 未取得時の曜日ベースフォールバック、DB 値優先のロジック、最大探索日数制限、カレンダー更新バッチ job（calendar_update_job）を実装。
    - J-Quants クライアント経由の差分取得・保存処理との連携点を用意。
  - src/kabusys/data/pipeline.py を追加。
    - ETL パイプラインの骨格を実装。差分取得、保存、品質チェックのフロー設計。
    - ETLResult データクラスを実装（target_date / fetched/saved counts / quality_issues / errors など）。
    - DuckDB 互換性を考慮したテーブル存在チェックや最大日付取得ユーティリティを提供。
  - src/kabusys/data/etl.py で ETLResult を再エクスポート。
- 研究（Research）モジュール:
  - src/kabusys/research/factor_research.py を追加。
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER / ROE）などを DuckDB 上で計算する関数（calc_momentum / calc_volatility / calc_value）を実装。
    - SQL ウィンドウ関数を活用した安定的な集計を実装。データ不足時は None を返す設計。
  - src/kabusys/research/feature_exploration.py を追加。
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク変換（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等外部依存を使わない実装で、ランク処理における同順位の平均ランク処理や ties 対策を実装。
  - src/kabusys/research/__init__.py で公開 API を整理（calc_momentum 等をエクスポート）。
- その他ユーティリティ／設計上の配慮:
  - DuckDB を前提とした SQL 実装。
  - ルックアヘッドバイアス防止（datetime.today() などを使用しない方針）をプロジェクト全体で徹底。
  - OpenAI 呼び出し部に対してテスト時に差し替え可能な設計（モックしやすい）。
  - ロギングと警告の充実（テスト・運用での可観測性向上）。
  - jquants_client / quality など外部モジュールとの連携ポイントを用意（本実装は依存を注入して利用する設計）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- なし

Removed
- なし

Security
- OpenAI API キーは引数で注入可能かつ環境変数 OPENAI_API_KEY を参照する方式。キー未設定時は明示的にエラーを返す実装（誤使用を防止）。

Notes / 補足
- OpenAI API レスポンスのパースで冗長テキストが混入するケースに対して JSON 部分抽出のリカバリ処理を実装しており、LLM の出力ばらつきに耐性があります。
- DuckDB の executemany の挙動差（空リストバインド不可）を考慮した実装が各所に含まれています（互換性対策）。
- 設計方針として「外部発注 API へはアクセスしない」「DB/過去データのみを参照する」ことを明記しており、研究／検証フェーズでの安全性を重視しています。

今後の予定（想定）
- telemetry / モニタリング統合（Slack 通知等）の追加。
- strategy / execution / monitoring の具体実装（現在はパッケージ公開名として存在）。
- ETL の詳細な品質検出ルール（quality モジュール）の実装強化。
- テストケース（ユニット／統合）と CI 設定の整備。

--- 

この CHANGELOG は、提示されたソースコードからの推測に基づいて作成しています。必要があれば、実際のコミット履歴やリポジトリのタグ情報に合わせて日付や変更内容を調整してください。