# KabuSys

KabuSys は日本株の自動売買システム（骨組み）のための Python パッケージです。本リポジトリはプロジェクトの基本構造（データ取得、ストラテジ、注文実行、監視）を提供します。各サブパッケージは拡張・実装することで実際の自動売買システムとして利用できます。

バージョン: 0.1.0

---

## 概要

このプロジェクトは以下の責務ごとにレイヤーを分離した設計を想定しています。

- data: 市場データの取得・前処理（例えば板情報、約定履歴、OHLC 等）
- strategy: 売買戦略（シグナル生成、ポジション管理）
- execution: 注文送信・約定管理（証券会社 API などとのやり取り）
- monitoring: ログ・メトリクス・アラート（稼働状況の監視）

現在はパッケージの骨組みが含まれており、各モジュールの実装はこれから追加します。拡張しやすい構成を意図しています。

---

## 機能一覧（予定 / 推奨実装）

- データ取得モジュール（リアルタイム / 履歴）
- ストラテジ実装のプラグイン機構
- 注文管理（成行、指値、キャンセル、注文状態の追跡）
- リスク管理（最大ポジション、損切りルール等）
- 監視ダッシュボード（ログ、パフォーマンス指標、アラート）
- 設定・認証管理（APIキー等の安全な管理）

> 注意: 現行リポジトリは設計骨組みのみで、上記の具象実装は含まれていません。各機能は今後の実装または利用者による実装を想定しています。

---

## セットアップ手順

1. 必須環境
   - Python 3.8 以上（プロジェクト要件に応じて調整してください）

2. リポジトリをクローン
   ```
   git clone <このリポジトリの URL>
   cd <リポジトリ名>
   ```

3. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

4. 開発インストール
   - setup.py / pyproject.toml がある場合:
     ```
     pip install -e .
     ```
   - まだパッケージ化していない場合は、直接ソースパスを PYTHONPATH に加えるか、上記の editable インストールを行ってください。

5. 依存パッケージ
   - 本骨組みには外部依存が含まれていません。実装時に必要なライブラリ（requests、pandas、numpy、websocket-client 等）を requirements.txt または pyproject.toml に追加してください。

6. 環境変数 / 機密情報
   - 実際の注文実行を行う場合は API キー等を利用します。鍵情報は環境変数や専用のシークレット管理（Vault 等）で保護してください。ソースコードにハードコードしないでください。

---

## 使い方（基本）

現状のパッケージはサブパッケージの骨組みを提供します。以下は基本的なインポート例です。

Python からパッケージのバージョンやサブパッケージを参照する例:
```python
import kabusys

print(kabusys.__version__)      # 0.1.0
import kabusys.data
import kabusys.strategy
import kabusys.execution
import kabusys.monitoring
```

サブパッケージに実装を追加する際のガイドライン（例）:
- data パッケージ:
  - MarketDataClient クラス（API からデータを取得）
  - DataLoader / Preprocessor（pandas データフレームを返す）
- strategy パッケージ:
  - StrategyBase 抽象クラス（on_bar, on_tick などのコールバック）
  - 複数ストラテジをプラグインとして読み込める仕組み
- execution パッケージ:
  - BrokerClient 抽象クラス（send_order, cancel_order, get_order_status）
  - 実際の API 用の実装（kabu API 等）
- monitoring パッケージ:
  - Logger / MetricsCollector（Prometheus, Grafana などと連携）

サンプル：簡単なストラテジの流れ（擬似コード）
```python
# data からデータ取得
market_data = kabusys.data.MarketDataClient(...).get_latest(symbol)

# strategy でシグナル生成
signal = my_strategy.on_tick(market_data)

# execution で注文送信
if signal == "BUY":
    kabusys.execution.BrokerClient(...).send_order(symbol, qty, side="BUY")
```

実装時は抽象クラスやインターフェースを定義して、テスト可能で差し替え可能な設計にすることを推奨します。

---

## ディレクトリ構成

現状の主なファイル・ディレクトリは以下の通りです。

- src/
  - kabusys/
    - __init__.py           # パッケージのエントリ（__version__ 等）
    - data/
      - __init__.py         # data サブパッケージ（市場データ関連）
    - strategy/
      - __init__.py         # strategy サブパッケージ（売買戦略）
    - execution/
      - __init__.py         # execution サブパッケージ（注文実行）
    - monitoring/
      - __init__.py         # monitoring サブパッケージ（監視）

README などのトップレベルファイルはプロジェクトルートに配置してください（この README.md）。

---

## 実装・拡張のヒント

- 抽象クラスを設けて依存性注入（DI）を利用するとテストしやすくなります。
- 注文実行部分は必ずサンドボックス環境で十分にテストしてから本番 API を叩いてください。
- ロギングと監視を早い段階で組み込むと、実稼働時のトラブルシュートが容易になります。
- バックテスト用の機構を strategy 層と切り離して実装すると、同一ロジックでオンライントレードとバックテストを共有できます。

---

## 貢献

1. Issue を立てて仕様や提案を議論してください。
2. Fork → ブランチ作成 → Pull Request の流れでお願いします。
3. コードスタイルやテストを追加してから PR を作成してください。

---

## ライセンス

このリポジトリのライセンスファイル（LICENSE）が無い場合は、適切なライセンスを追加してください（例: MIT, Apache-2.0 等）。

---

この README は現状のソース（パッケージ骨組み）に基づく導入・拡張ガイドです。具体的な API 実装やサードパーティ連携は各サブパッケージに実装を追加してください。必要であれば、各サブパッケージのテンプレートやサンプル実装を作成するサポートもできます。