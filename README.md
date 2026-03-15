# KabuSys

KabuSys は「日本株自動売買システム」のための Python パッケージの骨組み（スケルトン）です。本リポジトリはモジュール分割（データ取得、戦略、注文実行、監視）を想定した構造を提供します。実運用に使うには各モジュールに実装を追加してください。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを設計・実装するための基礎パッケージです。内部は責務ごとにモジュールを分けており、個別の実装（データプロバイダ、売買戦略、注文実行アダプタ、監視/ロギング）を差し替えやすい構成になっています。

主な設計方針:
- 関心事の分離（データ、戦略、実行、監視）
- 実装の差し替えや拡張が容易な構造
- シンプルで分かりやすい API の入口

注意: 現在は「骨組み」の状態です。実際の売買処理や外部 API 連携は実装されていません。実運用する場合は十分なテスト・リスク管理を行ってください。

---

## 機能一覧（想定／骨組み）

- データ取得（data）
  - 株価や板情報などを取得するためのプロバイダを配置する想定
- 戦略（strategy）
  - トレード戦略（エントリー／イグジットロジック）を実装する場所
- 注文実行（execution）
  - 実際の発注ロジックやブローカ API とのアダプタを実装する場所
- 監視（monitoring）
  - ログ、アラート、死活監視などを実装する場所

各機能はサブパッケージとして分離されており、独立に実装・テストできます。

---

## 必要条件

- Python 3.8 以上（プロジェクト方針に合わせて適宜変更してください）
- pip（パッケージのインストール時）

（外部 API や特定ライブラリを使う場合はそれらの依存関係を追加してください）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <リポジトリ URL>
   cd <リポジトリ ディレクトリ>
   ```

2. 仮想環境を作成して有効化（推奨）
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```
     python -m venv .venv
     .venv\Scripts\activate
     ```

3. パッケージをインストール（開発時は編集可能インストール）
   - プロジェクトに packaging（pyproject.toml / setup.py）がある場合:
     ```
     pip install -e .
     ```
   - ない場合は、リポジトリのルートから直接 Python パスに追加してインポートできます。

4. 必要な追加依存があれば requirements.txt や pyproject.toml に従ってインストールしてください。

---

## 使い方（基本）

現在はモジュールのスケルトンのみ実装されています。パッケージの読み込みやバージョン確認は可能です。

例:
```python
import kabusys

print(kabusys.__version__)  # "0.1.0"
```

サブパッケージを参照する例:
```python
import kabusys.data      # データプロバイダを実装する場所
import kabusys.strategy  # 戦略の実装場所
import kabusys.execution # 注文実行アダプタ
import kabusys.monitoring# 監視・ロギング
```

各サブパッケージに具体的なクラスや関数を実装したら、それらをインポートして実行することでトレードフローを構築します。

簡単な設計例（擬似コード）:
```python
from kabusys.data import MarketDataProvider
from kabusys.strategy import MyStrategy
from kabusys.execution import ExecutionAdapter
from kabusys.monitoring import Monitor

# 1) データプロバイダを初期化（APIキー等を渡す）
data_provider = MarketDataProvider(api_key="XXX")

# 2) 戦略にデータプロバイダを渡す
strategy = MyStrategy(data_provider)

# 3) 実行アダプタを初期化
executor = ExecutionAdapter(config={...})

# 4) 監視を開始
monitor = Monitor()

# 5) ループまたはスケジューラで戦略を実行し、シグナルがあれば executor に渡す
signal = strategy.generate_signal()
if signal:
    executor.execute(signal)
    monitor.record(signal)
```

（上はインターフェース設計の一例です。実装はプロジェクト要件に合わせて作成してください。）

---

## 拡張方法（ガイドライン）

- data:
  - データ取得ロジック（REST/WebSocket）やキャッシュ処理を実装する。
  - 取得形式は戦略側が扱いやすい統一フォーマットに変換する。

- strategy:
  - 単一責任の戦略クラスを作成（initialize / on_tick / generate_signal など）。
  - 複数戦略の組み合わせやバックテスト機能を追加可能。

- execution:
  - ブローカ（kabuステーション、各社 API）ごとのアダプタを実装。
  - 発注前に許容リスクチェックやサーキットブレーカ処理を入れる。

- monitoring:
  - ログ、メトリクス（Prometheus 等）、アラート（メール/チャット）を統合。
  - ダッシュボードと連携することで運用性を向上できる。

実装時はモックを用いたユニットテストを充実させ、実環境と同等のテストを行ってから外部 API へ接続してください。

---

## ディレクトリ構成

当リポジトリの主要ファイル/ディレクトリ構成は以下の通りです。

- src/
  - kabusys/
    - __init__.py          # パッケージ定義（バージョン等）
    - data/
      - __init__.py        # データ取得関連モジュール
    - strategy/
      - __init__.py        # 戦略関連モジュール
    - execution/
      - __init__.py        # 注文実行関連モジュール
    - monitoring/
      - __init__.py        # 監視・ロギング関連モジュール

ファイル（現状の中身）:
- src/kabusys/__init__.py
  - パッケージのメタデータ（__version__= "0.1.0"）
  - __all__ = ["data", "strategy", "execution", "monitoring"]

サブパッケージはすべてプレースホルダ（空の __init__.py）です。実装を追加してください。

---

## 注意事項（重要）

- 実際の売買を行う前に必ず十分なバックテスト・シミュレーションを行ってください。
- API キーや秘密情報は環境変数や安全なシークレット管理手法で管理し、ソースにハードコードしないでください。
- 金融商品取引に関する法令や証券会社の利用規約を遵守してください。
- 本プロジェクトはサンプル／雛形であり、運用に関していかなる保証も行いません。

---

## 貢献・ライセンス

- 貢献歓迎。Issue / Pull Request を送ってください。
- ライセンスはリポジトリに LICENSE ファイルを追加してください（例: MIT, Apache-2.0 など）。

---

必要であれば、README をプロジェクトの実装状況や目的に合わせてカスタマイズします。たとえば「kabuステーション API の具体的な接続方法」「バックテストフレームワークの統合例」「サンプル戦略の実装」などを追加できます。どの内容を追記したいか教えてください。